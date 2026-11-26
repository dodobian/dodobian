// SPDX-License-Identifier: GPL-2.0-or-later
// Copyright (C) 2026 The Dodobian authors
//
// Draw one frame of one case on software GLES2 (Mesa llvmpipe) and exit: 0 when the frame was
// drawn and read back, 2 when the case could not be set up. A crash in llvmpipe kills the process
// with a signal, so run.sh starts each case as its own process and reports which ones die.
//
// Usage: probe <case> [output.ppm]   probe --list
//
// Why: our Labwc with SceneFX crashes llvmpipe's rasterizer on amd64 (not on arm64; Weston on the
// same llvmpipe is fine), right after the 10x16 cursor buffer gets its framebuffer. Suspects:
// SceneFX's shaders; the stencil renderbuffer SceneFX attaches to every framebuffer
// (render/fx_renderer/fx_framebuffer.c), which wlroots and Weston do not have; and the cursor
// buffer itself: wlroots' udmabuf allocator gives it a stride of width * 4, 40 bytes, not a
// multiple of 16.
//   scene:*  SceneFX's scene graph on a headless wlroots output, the same path Labwc renders
//            through (udmabuf buffers, SceneFX framebuffer with its stencil attachment).
//   wlr:*    the same output with wlroots' own GLES2 renderer, without SceneFX.
//   gl:*     plain EGL (Mesa's software device, as wlroots picks it) and GLES2 without wlroots:
//            SceneFX's base shaders (shaders.h) drawn into a renderbuffer, optionally 10x16
//            (-small), backed by a udmabuf with a stride of width * 4 (-dmabuf), with a stencil
//            attachment (-stencil). A crashing gl:* case is a Mesa reproducer on its own.
// The frame is always read back (glFinish), so llvmpipe has rasterized it before the process exits.
#define _GNU_SOURCE
#include <EGL/egl.h>
#include <EGL/eglext.h>
#include <GLES2/gl2.h>
#include <GLES2/gl2ext.h>
#include <drm_fourcc.h>
#include <fcntl.h>
#include <linux/udmabuf.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/mman.h>
#include <unistd.h>
#include <wayland-server-core.h>
#include <wlr/backend.h>
#include <wlr/backend/headless.h>
#include <wlr/interfaces/wlr_buffer.h>
#include <wlr/render/allocator.h>
#include <wlr/render/wlr_renderer.h>
#include <wlr/render/wlr_texture.h>
#include <wlr/types/wlr_buffer.h>
#include <wlr/types/wlr_output.h>
#include <wlr/util/log.h>
#include <scenefx/render/fx_renderer/fx_renderer.h>
#include <scenefx/types/wlr_scene.h>
#include "shaders.h"

#define W 1280
#define H 720

static void fail(const char *what) {
	fprintf(stderr, "probe: %s\n", what);
	exit(2);
}

// Write the w x h frame as PPM. bgr: bytes in memory are B, G, R, X (DRM ARGB/XRGB8888 on little
// endian).
static void write_ppm(const char *path, const uint8_t *px, int w, int h, bool bgr) {
	unsigned long lit = 0;
	for (int i = 0; i < w * h; i++) {
		const uint8_t *p = px + i * 4;
		if (p[0] || p[1] || p[2]) {
			lit++;
		}
	}
	printf("frame read back: %lu of %d pixels not black\n", lit, w * h);
	if (!path) {
		return;
	}
	FILE *f = fopen(path, "wb");
	if (!f) {
		fail("cannot write the frame");
	}
	fprintf(f, "P6\n%d %d\n255\n", w, h);
	for (int i = 0; i < w * h; i++) {
		const uint8_t *p = px + i * 4;
		uint8_t rgb[3] = { bgr ? p[2] : p[0], p[1], bgr ? p[0] : p[2] };
		fwrite(rgb, 1, 3, f);
	}
	fclose(f);
}

// --- a wlr_buffer in plain memory (what Labwc's cursor and its own buffers are)

struct mem_buffer {
	struct wlr_buffer base;
	uint32_t format;
	uint32_t *data;
};

static void mem_destroy(struct wlr_buffer *b) {
	struct mem_buffer *m = wl_container_of(b, m, base);
	free(m->data);
	free(m);
}

static bool mem_begin(struct wlr_buffer *b, uint32_t flags, void **data, uint32_t *format,
		size_t *stride) {
	(void)flags;
	struct mem_buffer *m = wl_container_of(b, m, base);
	*data = m->data;
	*format = m->format;
	*stride = (size_t)b->width * 4;
	return true;
}

static void mem_end(struct wlr_buffer *b) {
	(void)b;
}

static const struct wlr_buffer_impl mem_impl = {
	.destroy = mem_destroy,
	.begin_data_ptr_access = mem_begin,
	.end_data_ptr_access = mem_end,
};

// A test pattern: a colour gradient; with alpha, a transparent border and a half-transparent band,
// like a cursor image. Pixels are premultiplied.
static struct wlr_buffer *pattern_buffer(int w, int h, bool alpha) {
	struct mem_buffer *m = calloc(1, sizeof(*m));
	m->data = calloc((size_t)w * h, 4);
	if (!m->data) {
		fail("out of memory");
	}
	m->format = alpha ? DRM_FORMAT_ARGB8888 : DRM_FORMAT_XRGB8888;
	for (int y = 0; y < h; y++) {
		for (int x = 0; x < w; x++) {
			uint32_t a = 255;
			if (alpha && (x == 0 || y == 0 || x == w - 1 || y == h - 1)) {
				a = 0;
			} else if (alpha && y < h / 3) {
				a = 128;
			}
			uint32_t r = (uint32_t)(x * 255 / (w > 1 ? w - 1 : 1)) * a / 255;
			uint32_t g = (uint32_t)(y * 255 / (h > 1 ? h - 1 : 1)) * a / 255;
			uint32_t b = 160 * a / 255;
			m->data[y * w + x] = a << 24 | r << 16 | g << 8 | b;
		}
	}
	wlr_buffer_init(&m->base, &mem_impl, w, h);
	return &m->base;
}

// --- scene:* cases, through SceneFX's scene graph

struct scene_probe {
	struct wlr_renderer *renderer;
	struct wlr_output *output;
	struct wlr_scene *scene;
	struct wlr_scene_output *scene_output;
};

// A headless output, enabled, rendered by SceneFX (fx) or by wlroots' own renderer.
static void output_setup(struct scene_probe *p, bool fx) {
	struct wl_display *display = wl_display_create();
	struct wlr_backend *backend = wlr_headless_backend_create(wl_display_get_event_loop(display));
	if (!backend) {
		fail("no headless backend");
	}
	p->renderer = fx ? fx_renderer_create(backend) : wlr_renderer_autocreate(backend);
	if (!p->renderer) {
		fail("no renderer");
	}
	struct wlr_allocator *allocator = wlr_allocator_autocreate(backend, p->renderer);
	if (!allocator) {
		fail("no allocator");
	}
	p->output = wlr_headless_add_output(backend, W, H);
	if (!p->output || !wlr_output_init_render(p->output, allocator, p->renderer)) {
		fail("no output");
	}
	if (!wlr_backend_start(backend)) {
		fail("backend does not start");
	}
	struct wlr_output_state state;
	wlr_output_state_init(&state);
	wlr_output_state_set_enabled(&state, true);
	wlr_output_state_set_custom_mode(&state, W, H, 0);
	if (!wlr_output_commit_state(p->output, &state)) {
		fail("output does not enable");
	}
	wlr_output_state_finish(&state);
}

static void scene_setup(struct scene_probe *p) {
	output_setup(p, true);
	// Always render: with a single buffer on screen the scene would hand that buffer to the
	// output as it is (direct scan-out) and nothing would be drawn.
	setenv("WLR_SCENE_DISABLE_DIRECT_SCANOUT", "1", 1);
	p->scene = wlr_scene_create();
	p->scene_output = wlr_scene_output_create(p->scene, p->output);
}

// Read a buffer back through the renderer (which waits for drawing with glFinish) and write it.
static void read_back(struct wlr_renderer *renderer, struct wlr_buffer *buffer, const char *ppm) {
	struct wlr_texture *tex = wlr_texture_from_buffer(renderer, buffer);
	if (!tex) {
		fail("buffer cannot be read back");
	}
	uint32_t format = wlr_texture_preferred_read_format(tex);
	bool bgr = format == DRM_FORMAT_ARGB8888 || format == DRM_FORMAT_XRGB8888;
	if (!bgr && format != DRM_FORMAT_ABGR8888 && format != DRM_FORMAT_XBGR8888) {
		fprintf(stderr, "probe: read format 0x%08x\n", format);
		fail("unexpected read format");
	}
	int w = buffer->width, h = buffer->height;
	uint8_t *px = malloc((size_t)w * h * 4);
	struct wlr_texture_read_pixels_options opts = {
		.data = px,
		.format = format,
		.stride = w * 4,
	};
	if (!px || !wlr_texture_read_pixels(tex, &opts)) {
		fail("read back failed");
	}
	write_ppm(ppm, px, w, h, bgr);
	wlr_texture_destroy(tex);
	free(px);
}

static void scene_frame(struct scene_probe *p, const char *ppm) {
	struct wlr_output_state state;
	wlr_output_state_init(&state);
	if (!wlr_scene_output_build_state(p->scene_output, &state, NULL)) {
		fail("scene does not build a frame");
	}
	if (!(state.committed & WLR_OUTPUT_STATE_BUFFER) || !state.buffer) {
		fail("scene built a state without a frame");
	}
	if (state.buffer->width != W || state.buffer->height != H) {
		fail("the frame is not the output's size: the scene did not render it");
	}
	read_back(p->renderer, state.buffer, ppm);
	wlr_output_commit_state(p->output, &state);
	wlr_output_state_finish(&state);
}

static struct wlr_scene_buffer *add_buffer(struct scene_probe *p, int w, int h, bool alpha,
		int x, int y) {
	struct wlr_buffer *b = pattern_buffer(w, h, alpha);
	struct wlr_scene_buffer *sb = wlr_scene_buffer_create(&p->scene->tree, b);
	wlr_buffer_drop(b);
	wlr_scene_node_set_position(&sb->node, x, y);
	return sb;
}

static int run_scene(const char *name, const char *ppm) {
	static const float opaque[4] = { 0.8f, 0.2f, 0.1f, 1.0f };
	static const float half[4] = { 0.1f, 0.3f, 0.4f, 0.5f }; // premultiplied
	static const float shadow[4] = { 0.3f, 0.0f, 0.5f, 0.6f }; // coloured: visible on black
	struct scene_probe p;
	scene_setup(&p);
	struct wlr_scene_tree *root = &p.scene->tree;

	if (!strcmp(name, "scene:empty")) {
		// nothing: the background only
	} else if (!strcmp(name, "scene:rect")) {
		struct wlr_scene_rect *r = wlr_scene_rect_create(root, 400, 300, opaque);
		wlr_scene_node_set_position(&r->node, 100, 100);
	} else if (!strcmp(name, "scene:rect-alpha")) {
		struct wlr_scene_rect *r = wlr_scene_rect_create(root, 400, 300, half);
		wlr_scene_node_set_position(&r->node, 100, 100);
	} else if (!strcmp(name, "scene:rect-round")) {
		struct wlr_scene_rect *r = wlr_scene_rect_create(root, 400, 300, opaque);
		wlr_scene_node_set_position(&r->node, 100, 100);
		wlr_scene_rect_set_corner_radius(r, 12);
	} else if (!strcmp(name, "scene:buffer-rgba")) {
		add_buffer(&p, 10, 16, true, 100, 100);
	} else if (!strcmp(name, "scene:buffer-rgbx")) {
		add_buffer(&p, 400, 300, false, 100, 100);
	} else if (!strcmp(name, "scene:buffer-round")) {
		struct wlr_scene_buffer *sb = add_buffer(&p, 400, 300, true, 100, 100);
		wlr_scene_buffer_set_corner_radius(sb, 12);
	} else if (!strcmp(name, "scene:shadow")) {
		struct wlr_scene_shadow *s = wlr_scene_shadow_create(root, 440, 340, 12, 20.0f, shadow);
		wlr_scene_node_set_position(&s->node, 80, 80);
		struct wlr_scene_rect *r = wlr_scene_rect_create(root, 400, 300, opaque);
		wlr_scene_node_set_position(&r->node, 100, 100);
	} else if (!strcmp(name, "scene:blur")) {
		wlr_scene_set_blur_data(p.scene, 3, 5, 0.02f, 0.9f, 0.9f, 1.1f);
		add_buffer(&p, 400, 300, false, 100, 100);
		struct wlr_scene_blur *b = wlr_scene_blur_create(root, 300, 200);
		wlr_scene_node_set_position(&b->node, 200, 150);
	} else if (!strcmp(name, "scene:cursor")) {
		// A cursor drawn into the frame (software cursor), 10x16 ARGB: the headless backend would
		// otherwise take it as a hardware cursor and leave it out of the frame.
		wlr_output_lock_software_cursors(p.output, true);
		struct wlr_output_cursor *c = wlr_output_cursor_create(p.output);
		struct wlr_buffer *b = pattern_buffer(10, 16, true);
		if (!c || !wlr_output_cursor_set_buffer(c, b, 0, 0)) {
			fail("no cursor");
		}
		wlr_buffer_drop(b);
		wlr_output_cursor_move(c, 100, 100);
	} else if (!strcmp(name, "scene:cursor-hw")) {
		// The cursor as Labwc gets it on the headless backend: a "hardware" cursor. wlroots draws
		// the image into a cursor buffer of its own, 10x16 from udmabuf, which SceneFX gives a
		// framebuffer with its stencil attachment; Labwc's crash on amd64 comes right after
		// "Created GL FBO for buffer 10x16". The frame itself stays black.
		struct wlr_output_cursor *c = wlr_output_cursor_create(p.output);
		struct wlr_buffer *b = pattern_buffer(10, 16, true);
		if (!c || !wlr_output_cursor_set_buffer(c, b, 0, 0)) {
			fail("no cursor");
		}
		wlr_buffer_drop(b);
		wlr_output_cursor_move(c, 100, 100);
	} else {
		return -1;
	}
	scene_frame(&p, ppm);
	return 0;
}

// --- wlr:* cases, wlroots without SceneFX

static int run_wlr(const char *name, const char *ppm) {
	if (strcmp(name, "wlr:cursor-hw")) {
		return -1;
	}
	// scene:cursor-hw without SceneFX: wlroots' GLES2 renderer draws the cursor image into its
	// 10x16 udmabuf cursor buffer (no stencil attachment); the cursor buffer is read back.
	struct scene_probe p;
	output_setup(&p, false);
	struct wlr_output_cursor *c = wlr_output_cursor_create(p.output);
	struct wlr_buffer *b = pattern_buffer(10, 16, true);
	if (!c || !wlr_output_cursor_set_buffer(c, b, 0, 0)) {
		fail("no cursor");
	}
	wlr_buffer_drop(b);
	if (!p.output->cursor_front_buffer) {
		fail("no hardware cursor buffer");
	}
	read_back(p.renderer, p.output->cursor_front_buffer, ppm);
	return 0;
}

// --- gl:* cases, plain EGL and GLES2

// A udmabuf of at least size bytes, as wlroots' udmabuf allocator makes one.
static int udmabuf_create(size_t size) {
	int dev = open("/dev/udmabuf", O_RDWR | O_CLOEXEC);
	if (dev < 0) {
		fail("no /dev/udmabuf");
	}
	long page = sysconf(_SC_PAGE_SIZE);
	size = (size + page - 1) / page * page;
	int memfd = memfd_create("probe", MFD_CLOEXEC | MFD_ALLOW_SEALING);
	if (memfd < 0 || ftruncate(memfd, size) < 0 || fcntl(memfd, F_ADD_SEALS, F_SEAL_SHRINK) < 0) {
		fail("no memfd for the udmabuf");
	}
	struct udmabuf_create create = {
		.memfd = memfd,
		.flags = UDMABUF_FLAGS_CLOEXEC,
		.offset = 0,
		.size = size,
	};
	int fd = ioctl(dev, UDMABUF_CREATE, &create);
	if (fd < 0) {
		fail("UDMABUF_CREATE failed");
	}
	close(memfd);
	close(dev);
	return fd;
}

// Mesa's software EGL device, which wlroots uses for llvmpipe (EGL_PLATFORM_DEVICE_EXT).
static EGLDisplay software_display(void) {
	PFNEGLQUERYDEVICESEXTPROC query_devices =
		(PFNEGLQUERYDEVICESEXTPROC)eglGetProcAddress("eglQueryDevicesEXT");
	PFNEGLQUERYDEVICESTRINGEXTPROC query_string =
		(PFNEGLQUERYDEVICESTRINGEXTPROC)eglGetProcAddress("eglQueryDeviceStringEXT");
	PFNEGLGETPLATFORMDISPLAYEXTPROC get_display =
		(PFNEGLGETPLATFORMDISPLAYEXTPROC)eglGetProcAddress("eglGetPlatformDisplayEXT");
	if (!query_devices || !query_string || !get_display) {
		fail("no EGL device enumeration");
	}
	EGLDeviceEXT devices[16];
	EGLint n = 0;
	if (!query_devices(16, devices, &n)) {
		fail("eglQueryDevicesEXT failed");
	}
	for (EGLint i = 0; i < n; i++) {
		const char *exts = query_string(devices[i], EGL_EXTENSIONS);
		if (exts && strstr(exts, "EGL_MESA_device_software")) {
			return get_display(EGL_PLATFORM_DEVICE_EXT, devices[i], NULL);
		}
	}
	fail("no software EGL device");
	return EGL_NO_DISPLAY;
}

static GLuint compile(GLenum type, const char *src) {
	GLuint s = glCreateShader(type);
	glShaderSource(s, 1, &src, NULL);
	glCompileShader(s);
	GLint ok;
	glGetShaderiv(s, GL_COMPILE_STATUS, &ok);
	if (!ok) {
		char log[1024];
		glGetShaderInfoLog(s, sizeof(log), NULL, log);
		fprintf(stderr, "%s\n", log);
		fail("shader does not compile");
	}
	return s;
}

static GLuint program(const char *frag) {
	GLuint p = glCreateProgram();
	glAttachShader(p, compile(GL_VERTEX_SHADER, common_vert_src));
	glAttachShader(p, compile(GL_FRAGMENT_SHADER, frag));
	glLinkProgram(p);
	GLint ok;
	glGetProgramiv(p, GL_LINK_STATUS, &ok);
	if (!ok) {
		fail("program does not link");
	}
	return p;
}

// Draw the unit square at box (x, y, w, h) in pixels of an fw x fh target, as SceneFX does: the
// vertex shader computes pos3 * proj, so the row-major matrix is uploaded untransposed.
static void draw_box(GLuint prog, int x, int y, int w, int h, int fw, int fh) {
	float proj[9] = {
		2.0f * w / fw, 0, 2.0f * x / fw - 1,
		0, 2.0f * h / fh, 2.0f * y / fh - 1,
		0, 0, 1,
	};
	static const float ident[9] = { 1, 0, 0, 0, 1, 0, 0, 0, 1 };
	static const GLfloat verts[] = { 0, 0, 1, 0, 0, 1, 1, 0, 1, 1, 0, 1 };
	glUniformMatrix3fv(glGetUniformLocation(prog, "proj"), 1, GL_FALSE, proj);
	glUniformMatrix3fv(glGetUniformLocation(prog, "tex_proj"), 1, GL_FALSE, ident);
	GLint pos = glGetAttribLocation(prog, "pos");
	glEnableVertexAttribArray(pos);
	glVertexAttribPointer(pos, 2, GL_FLOAT, GL_FALSE, 0, verts);
	glDrawArrays(GL_TRIANGLES, 0, 6);
	glDisableVertexAttribArray(pos);
}

static int run_gl(const char *name, const char *ppm) {
	// gl:<kind>[-small][-dmabuf][-stencil]: -small draws into a 10x16 target (the size of the
	// cursor buffer Labwc crashes on) instead of 1280x720; -dmabuf backs the colour buffer with a
	// udmabuf of stride width * 4 (as wlroots allocates it); -stencil adds SceneFX's stencil.
	const char *what = name + 3;
	size_t len = strcspn(what, "-");
	bool small = false, dmabuf = false, stencil = false;
	for (const char *f = what + len; *f;) {
		f++; // the '-'
		size_t n = strcspn(f, "-");
		if (n == 5 && !strncmp(f, "small", 5) && !small && !dmabuf && !stencil) {
			small = true;
		} else if (n == 6 && !strncmp(f, "dmabuf", 6) && !dmabuf && !stencil) {
			dmabuf = true;
		} else if (n == 7 && !strncmp(f, "stencil", 7) && !stencil) {
			stencil = true;
		} else {
			return -1;
		}
		f += n;
	}
	const int fw = small ? 10 : W, fh = small ? 16 : H;
	enum { CLEAR, QUAD, TEX } kind;
	if (!strncmp(what, "clear", len) && len == 5) {
		kind = CLEAR;
	} else if (!strncmp(what, "quad", len) && len == 4) {
		kind = QUAD;
	} else if (!strncmp(what, "tex", len) && len == 3) {
		kind = TEX;
	} else {
		return -1;
	}

	EGLDisplay dpy = software_display();
	if (dpy == EGL_NO_DISPLAY || !eglInitialize(dpy, NULL, NULL) || !eglBindAPI(EGL_OPENGL_ES_API)) {
		fail("no software EGL display");
	}
	static const EGLint attribs[] = { EGL_CONTEXT_CLIENT_VERSION, 2, EGL_NONE };
	EGLContext ctx = eglCreateContext(dpy, EGL_NO_CONFIG_KHR, EGL_NO_CONTEXT, attribs);
	if (ctx == EGL_NO_CONTEXT || !eglMakeCurrent(dpy, EGL_NO_SURFACE, EGL_NO_SURFACE, ctx)) {
		fail("no GLES2 context");
	}
	printf("GL renderer: %s\n", (const char *)glGetString(GL_RENDERER));

	// The framebuffer: colour, and with -stencil a GL_STENCIL_INDEX8 renderbuffer like SceneFX's.
	GLuint fbo, color, sb;
	glGenRenderbuffers(1, &color);
	glBindRenderbuffer(GL_RENDERBUFFER, color);
	if (dmabuf) {
		// ARGB8888 with stride width * 4, as wlroots' udmabuf allocator makes the cursor buffer.
		PFNEGLCREATEIMAGEKHRPROC create_image =
			(PFNEGLCREATEIMAGEKHRPROC)eglGetProcAddress("eglCreateImageKHR");
		PFNGLEGLIMAGETARGETRENDERBUFFERSTORAGEOESPROC image_storage =
			(PFNGLEGLIMAGETARGETRENDERBUFFERSTORAGEOESPROC)eglGetProcAddress(
				"glEGLImageTargetRenderbufferStorageOES");
		if (!create_image || !image_storage) {
			fail("no EGLImage import");
		}
		int fd = udmabuf_create((size_t)fw * 4 * fh);
		const EGLint image_attribs[] = {
			EGL_WIDTH, fw,
			EGL_HEIGHT, fh,
			EGL_LINUX_DRM_FOURCC_EXT, DRM_FORMAT_ARGB8888,
			EGL_DMA_BUF_PLANE0_FD_EXT, fd,
			EGL_DMA_BUF_PLANE0_OFFSET_EXT, 0,
			EGL_DMA_BUF_PLANE0_PITCH_EXT, fw * 4,
			EGL_NONE,
		};
		EGLImageKHR image = create_image(dpy, EGL_NO_CONTEXT, EGL_LINUX_DMA_BUF_EXT, NULL,
			image_attribs);
		if (image == EGL_NO_IMAGE_KHR) {
			fail("dmabuf import failed");
		}
		image_storage(GL_RENDERBUFFER, image);
		printf("colour buffer: udmabuf %dx%d, stride %d\n", fw, fh, fw * 4);
	} else {
		glRenderbufferStorage(GL_RENDERBUFFER, GL_RGBA8_OES, fw, fh);
	}
	glGenFramebuffers(1, &fbo);
	glBindFramebuffer(GL_FRAMEBUFFER, fbo);
	glFramebufferRenderbuffer(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_RENDERBUFFER, color);
	if (stencil) {
		glGenRenderbuffers(1, &sb);
		glBindRenderbuffer(GL_RENDERBUFFER, sb);
		glRenderbufferStorage(GL_RENDERBUFFER, GL_STENCIL_INDEX8, fw, fh);
		glFramebufferRenderbuffer(GL_FRAMEBUFFER, GL_STENCIL_ATTACHMENT, GL_RENDERBUFFER, sb);
	}
	if (glCheckFramebufferStatus(GL_FRAMEBUFFER) != GL_FRAMEBUFFER_COMPLETE) {
		fail("framebuffer incomplete");
	}
	glViewport(0, 0, fw, fh);
	glClearColor(0, 0, 0, 1);
	glClear(GL_COLOR_BUFFER_BIT);

	char frag[4096];
	if (kind == QUAD) {
		// A half-transparent premultiplied rectangle, blended: SceneFX's quad shader, no effects.
		snprintf(frag, sizeof(frag), quad_frag_src, 0);
		GLuint prog = program(frag);
		glUseProgram(prog);
		glEnable(GL_BLEND);
		glBlendFunc(GL_ONE, GL_ONE_MINUS_SRC_ALPHA);
		glUniform4f(glGetUniformLocation(prog, "color"), 0.1f, 0.3f, 0.4f, 0.5f);
		if (small) {
			draw_box(prog, 0, 0, fw, fh, fw, fh);
		} else {
			draw_box(prog, 100, 100, 400, 300, fw, fh);
		}
	} else if (kind == TEX) {
		// A 10x16 ARGB8888 image uploaded as BGRA and blended, as SceneFX draws a cursor.
		snprintf(frag, sizeof(frag), tex_frag_src, 1, 0);
		GLuint prog = program(frag);
		struct wlr_buffer *b = pattern_buffer(10, 16, true);
		struct mem_buffer *m = wl_container_of(b, m, base);
		GLuint tex;
		glGenTextures(1, &tex);
		glActiveTexture(GL_TEXTURE0);
		glBindTexture(GL_TEXTURE_2D, tex);
		glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE);
		glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE);
		glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR);
		glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR);
		glTexImage2D(GL_TEXTURE_2D, 0, GL_BGRA_EXT, 10, 16, 0, GL_BGRA_EXT, GL_UNSIGNED_BYTE,
			m->data);
		glUseProgram(prog);
		glEnable(GL_BLEND);
		glBlendFunc(GL_ONE, GL_ONE_MINUS_SRC_ALPHA);
		glUniform1i(glGetUniformLocation(prog, "tex"), 0);
		glUniform1f(glGetUniformLocation(prog, "alpha"), 1.0f);
		// SceneFX sets this bool uniform with glUniform1f.
		glUniform1f(glGetUniformLocation(prog, "discard_transparent"), 0.0f);
		draw_box(prog, small ? 0 : 100, small ? 0 : 100, 10, 16, fw, fh);
		wlr_buffer_drop(b);
	}

	uint8_t *px = malloc((size_t)fw * fh * 4);
	if (!px) {
		fail("out of memory");
	}
	glFinish();
	glReadPixels(0, 0, fw, fh, GL_RGBA, GL_UNSIGNED_BYTE, px);
	if (glGetError() != GL_NO_ERROR) {
		fail("GL error");
	}
	write_ppm(ppm, px, fw, fh, false);
	free(px);
	return 0;
}

static const char *const cases[] = {
	"scene:empty", "scene:rect", "scene:rect-alpha", "scene:rect-round", "scene:buffer-rgba",
	"scene:buffer-rgbx", "scene:buffer-round", "scene:shadow", "scene:blur", "scene:cursor",
	"scene:cursor-hw", "wlr:cursor-hw",
	"gl:clear", "gl:clear-stencil", "gl:quad", "gl:quad-stencil", "gl:tex", "gl:tex-stencil",
	"gl:clear-small", "gl:clear-small-stencil", "gl:quad-small", "gl:quad-small-stencil",
	"gl:tex-small", "gl:tex-small-stencil",
	"gl:tex-dmabuf", "gl:tex-dmabuf-stencil",
	"gl:clear-small-dmabuf", "gl:clear-small-dmabuf-stencil", "gl:quad-small-dmabuf",
	"gl:quad-small-dmabuf-stencil", "gl:tex-small-dmabuf", "gl:tex-small-dmabuf-stencil",
};

int main(int argc, char *argv[]) {
	if (argc == 2 && !strcmp(argv[1], "--list")) {
		for (size_t i = 0; i < sizeof(cases) / sizeof(cases[0]); i++) {
			puts(cases[i]);
		}
		return 0;
	}
	if (argc < 2 || argc > 3) {
		fprintf(stderr, "usage: probe <case> [output.ppm] | probe --list\n");
		return 2;
	}
	wlr_log_init(WLR_DEBUG, NULL); // as labwc -d, to compare with Labwc's log
	const char *ppm = argc == 3 ? argv[2] : NULL;
	int rc = -1;
	if (!strncmp(argv[1], "scene:", 6)) {
		rc = run_scene(argv[1], ppm);
	} else if (!strncmp(argv[1], "wlr:", 4)) {
		rc = run_wlr(argv[1], ppm);
	} else if (!strncmp(argv[1], "gl:", 3)) {
		rc = run_gl(argv[1], ppm);
	}
	if (rc < 0) {
		fprintf(stderr, "probe: no such case: %s\n", argv[1]);
		return 2;
	}
	printf("ok %s\n", argv[1]);
	return 0;
}

/*
 * SPDX-License-Identifier: MIT
 *
 * The base shaders of SceneFX 0.5 (https://github.com/wlrfx/scenefx, tag 0.5,
 * render/fx_renderer/shaders/), copied so probe.c can draw with them on plain GLES2, without
 * SceneFX: common.vert and quad.frag unchanged; tex.frag without its EFFECTS branches (rounded
 * corners), which the probe does not use. SceneFX fills the "%d" in the preambles with snprintf
 * before compiling; probe.c does the same. SceneFX's licence:
 *
 * Copyright (c) 2017, 2018 Drew DeVault
 * Copyright (c) 2014 Jari Vetoniemi
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy of this software
 * and associated documentation files (the "Software"), to deal in the Software without
 * restriction, including without limitation the rights to use, copy, modify, merge, publish,
 * distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the
 * Software is furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in all copies or
 * substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING
 * BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
 * NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
 * DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
 */
#ifndef PROBE_SHADERS_H
#define PROBE_SHADERS_H

static const char common_vert_src[] =
	"uniform mat3 proj;\n"
	"uniform vec4 color;\n"
	"uniform mat3 tex_proj;\n"
	"attribute vec2 pos;\n"
	"varying vec4 v_color;\n"
	"varying vec2 v_texcoord;\n"
	"\n"
	"void main() {\n"
	"	vec3 pos3 = vec3(pos, 1.0);\n"
	"	gl_Position = vec4(pos3 * proj, 1.0);\n"
	"	v_color = color;\n"
	"	v_texcoord = (pos3 * tex_proj).xy;\n"
	"}\n";

/* Preamble: EFFECTS. With EFFECTS 0 SceneFX links it without corner_alpha.frag. */
static const char quad_frag_src[] =
	"#define EFFECTS %d\n"
	"\n"
	"#if !defined(EFFECTS)\n"
	"#error \"Missing shader preamble\"\n"
	"#endif\n"
	"\n"
	"#ifdef GL_FRAGMENT_PRECISION_HIGH\n"
	"precision highp float;\n"
	"#else\n"
	"precision mediump float;\n"
	"#endif\n"
	"\n"
	"varying vec4 v_color;\n"
	"varying vec2 v_texcoord;\n"
	"\n"
	"#if EFFECTS\n"
	"uniform vec2 clip_size;\n"
	"uniform vec2 clip_position;\n"
	"uniform float clip_radius_top_left;\n"
	"uniform float clip_radius_top_right;\n"
	"uniform float clip_radius_bottom_left;\n"
	"uniform float clip_radius_bottom_right;\n"
	"#endif\n"
	"\n"
	"float corner_alpha(vec2 size, vec2 position, bool is_cutout,\n"
	"		float radius_tl, float radius_tr, float radius_bl, float radius_br);\n"
	"\n"
	"void main() {\n"
	"#if EFFECTS\n"
	"	// Clipping\n"
	"	float clip_corner_alpha = corner_alpha(\n"
	"		clip_size - 1.0,\n"
	"		clip_position + 0.5,\n"
	"		true,\n"
	"		clip_radius_top_left,\n"
	"		clip_radius_top_right,\n"
	"		clip_radius_bottom_left,\n"
	"		clip_radius_bottom_right\n"
	"	);\n"
	"\n"
	"	gl_FragColor = v_color * clip_corner_alpha;\n"
	"#else\n"
	"	gl_FragColor = v_color;\n"
	"#endif\n"
	"}\n";

/* Preamble: SOURCE (1 RGBA, 2 RGBX, 3 external), EFFECTS (kept for the preamble; must be 0 here). */
static const char tex_frag_src[] =
	"#define SOURCE %d\n"
	"#define EFFECTS %d\n"
	"\n"
	"#define SOURCE_TEXTURE_RGBA 1\n"
	"#define SOURCE_TEXTURE_RGBX 2\n"
	"#define SOURCE_TEXTURE_EXTERNAL 3\n"
	"\n"
	"#if !defined(SOURCE) || !defined(EFFECTS)\n"
	"#error \"Missing shader preamble\"\n"
	"#endif\n"
	"\n"
	"#if SOURCE == SOURCE_TEXTURE_EXTERNAL\n"
	"#extension GL_OES_EGL_image_external : require\n"
	"#endif\n"
	"\n"
	"#ifdef GL_FRAGMENT_PRECISION_HIGH\n"
	"precision highp float;\n"
	"#else\n"
	"precision mediump float;\n"
	"#endif\n"
	"\n"
	"varying vec2 v_texcoord;\n"
	"\n"
	"#if SOURCE == SOURCE_TEXTURE_EXTERNAL\n"
	"uniform samplerExternalOES tex;\n"
	"#elif SOURCE == SOURCE_TEXTURE_RGBA || SOURCE == SOURCE_TEXTURE_RGBX\n"
	"uniform sampler2D tex;\n"
	"#endif\n"
	"\n"
	"uniform float alpha;\n"
	"\n"
	"uniform bool discard_transparent;\n"
	"\n"
	"vec4 sample_texture() {\n"
	"#if SOURCE == SOURCE_TEXTURE_RGBA || SOURCE == SOURCE_TEXTURE_EXTERNAL\n"
	"	return texture2D(tex, v_texcoord);\n"
	"#elif SOURCE == SOURCE_TEXTURE_RGBX\n"
	"	return vec4(texture2D(tex, v_texcoord).rgb, 1.0);\n"
	"#endif\n"
	"}\n"
	"\n"
	"void main() {\n"
	"	gl_FragColor = sample_texture() * alpha;\n"
	"\n"
	"	if (discard_transparent && gl_FragColor.a == 0.0) {\n"
	"		discard;\n"
	"	}\n"
	"}\n";

#endif

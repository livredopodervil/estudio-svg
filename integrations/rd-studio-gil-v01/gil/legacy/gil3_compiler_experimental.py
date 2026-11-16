#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gil3_compiler_experimental.py

Compilador experimental GIL3 -> SVG.

Suporta:
- stage
- palette
- style
- shape
- object
- scene/layer/place
- anchors em shape e object
- use com:
  - attach { child-anchor ... parent-anchor ... }
  - fit { box W H }
  - rotate A
  - pivot ANCHOR
- repeat radial com:
  - count
  - source
  - style
  - origin
  - radius
  - start-angle
  - step-angle
  - fit { box W H }
  - child-anchor
  - orient radial-out
  - pivot

Limitações:
- linguagem nova e experimental
- não implementa herança/patch ainda
- não implementa grid/row/scatter
- não implementa blend/filtros/texto
- assume shapes em bbox local positiva (ex.: 0..1, 0..1)

Uso:
    python gil3_compiler_experimental.py arquivo.gil3 [saida.svg] [scene]
"""
from __future__ import annotations

import copy
import html
import math
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union


def esc(s: str) -> str:
    return html.escape(str(s), quote=True)

def fnum(x: Union[int, float, str]) -> str:
    if isinstance(x, str):
        return x
    if isinstance(x, int):
        return str(x)
    if abs(x - round(x)) < 1e-9:
        return str(int(round(x)))
    return f"{x:.6f}".rstrip("0").rstrip(".")

def strip_quotes(s: str) -> str:
    return s[1:-1] if len(s) >= 2 and s[0] == '"' and s[-1] == '"' else s

def clean_source(text: str) -> str:
    text = re.sub(r"//.*?$", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*#.*?$", "", text, flags=re.MULTILINE)
    return text

def tokenize(text: str) -> List[str]:
    token_re = re.compile(
        r'"[^"]*"|#[0-9A-Fa-f]{3,8}|-?\d+(?:\.\d+)?%?|[A-Za-z_][A-Za-z0-9_.-]*|[\(\)\{\}\[\],]'
    )
    return token_re.findall(clean_source(text))

def deep_copy(x):
    return copy.deepcopy(x)

def deg_to_rad(a: float) -> float:
    return a * math.pi / 180.0


@dataclass
class Stage:
    width: float = 1200
    height: float = 900
    viewbox: Tuple[float, float, float, float] = (0, 0, 1200, 900)
    background: Optional[str] = None

@dataclass
class GradientStop:
    offset: str
    color: str

@dataclass
class FillDef:
    kind: str = "solid"
    color: Optional[str] = None
    x1: Optional[float] = None
    y1: Optional[float] = None
    x2: Optional[float] = None
    y2: Optional[float] = None
    cx: Optional[float] = None
    cy: Optional[float] = None
    r: Optional[float] = None
    stops: List[GradientStop] = field(default_factory=list)

@dataclass
class Style:
    name: str
    fill: Optional[FillDef] = None
    stroke: Optional[str] = None
    stroke_width: Optional[float] = None
    opacity: Optional[float] = None

@dataclass
class Primitive:
    kind: str
    data: dict

@dataclass
class ShapeDef:
    name: str
    bbox: Tuple[float, float] = (1.0, 1.0)
    anchors: Dict[str, Tuple[float, float]] = field(default_factory=dict)
    primitive: Optional[Primitive] = None
    path_cmds: List[str] = field(default_factory=list)

@dataclass
class FitSpec:
    box: Optional[Tuple[float, float]] = None

@dataclass
class AttachSpec:
    child_anchor: str
    parent_anchor: str

@dataclass
class UseDecl:
    ref_name: str
    alias: Optional[str] = None
    style: Optional[str] = None
    attach: Optional[AttachSpec] = None
    fit: Optional[FitSpec] = None
    rotate: float = 0.0
    pivot: Optional[str] = None

@dataclass
class RepeatRadialDecl:
    alias: str
    count: int
    source: str
    style: Optional[str] = None
    origin: str = "center"
    radius: float = 0.0
    start_angle: float = 0.0
    step_angle: float = 0.0
    fit: Optional[FitSpec] = None
    child_anchor: str = "center"
    orient: Optional[str] = None
    pivot: Optional[str] = None

@dataclass
class ObjectDef:
    name: str
    anchors: Dict[str, Tuple[float, float]] = field(default_factory=dict)
    uses: List[UseDecl] = field(default_factory=list)
    repeats_radial: List[RepeatRadialDecl] = field(default_factory=list)

@dataclass
class PlaceDecl:
    ref_name: str
    alias: Optional[str] = None
    center: Tuple[float, float] = (0.5, 0.5)
    size: Tuple[float, float] = (1.0, 1.0)
    rotate: float = 0.0
    style: Optional[str] = None

@dataclass
class LayerDecl:
    name: str
    z: float = 0.0
    places: List[PlaceDecl] = field(default_factory=list)

@dataclass
class SceneDef:
    name: str
    layers: List[LayerDecl] = field(default_factory=list)

@dataclass
class Document:
    version: Optional[float] = None
    stage: Stage = field(default_factory=Stage)
    palette: Dict[str, str] = field(default_factory=dict)
    styles: Dict[str, Style] = field(default_factory=dict)
    shapes: Dict[str, ShapeDef] = field(default_factory=dict)
    objects: Dict[str, ObjectDef] = field(default_factory=dict)
    scenes: Dict[str, SceneDef] = field(default_factory=dict)


class ParseError(Exception):
    pass

class Parser:
    def __init__(self, text: str):
        self.tokens = tokenize(text)
        self.i = 0

    def eof(self) -> bool:
        return self.i >= len(self.tokens)

    def peek(self, n: int = 0) -> Optional[str]:
        idx = self.i + n
        return self.tokens[idx] if idx < len(self.tokens) else None

    def pop(self) -> str:
        if self.eof():
            raise ParseError("Fim inesperado do arquivo.")
        t = self.tokens[self.i]
        self.i += 1
        return t

    def expect(self, value: str) -> str:
        t = self.pop()
        if t != value:
            raise ParseError(f"Esperado '{value}', encontrado '{t}'.")
        return t

    def expect_string(self) -> str:
        t = self.pop()
        if not (t.startswith('"') and t.endswith('"')):
            raise ParseError(f"String esperada, encontrado: {t}")
        return strip_quotes(t)

    def expect_ident(self) -> str:
        t = self.pop()
        if not re.match(r"^[A-Za-z_][A-Za-z0-9_.-]*$", t):
            raise ParseError(f"Identificador inválido: {t}")
        return t

    def expect_number(self) -> float:
        t = self.pop()
        if t.endswith("%"):
            raise ParseError(f"Número esperado, encontrado percentual: {t}")
        try:
            return float(t)
        except ValueError:
            raise ParseError(f"Número esperado, encontrado: {t}")

    def expect_percent_or_number(self) -> str:
        t = self.pop()
        if re.match(r"^-?\d+(?:\.\d+)?%?$", t):
            return t
        raise ParseError(f"Percentual ou número esperado, encontrado: {t}")

    def parse_point(self) -> Tuple[float, float]:
        self.expect("(")
        x = self.expect_number()
        y = self.expect_number()
        self.expect(")")
        return x, y

    def parse_color_or_name(self) -> str:
        tok = self.pop()
        if tok.startswith("#"):
            return tok
        return strip_quotes(tok)

    def parse(self) -> Document:
        doc = Document()
        self.expect("gil3")
        if self.peek() and re.match(r"^-?\d+(?:\.\d+)?$", self.peek()):
            doc.version = self.expect_number()
        self.expect("{")
        while self.peek() != "}":
            tok = self.peek()
            if tok == "stage":
                doc.stage = self.parse_stage()
            elif tok == "palette":
                doc.palette = self.parse_palette()
            elif tok == "style":
                st = self.parse_style()
                doc.styles[st.name] = st
            elif tok == "shape":
                sh = self.parse_shape()
                doc.shapes[sh.name] = sh
            elif tok == "object":
                obj = self.parse_object()
                doc.objects[obj.name] = obj
            elif tok == "scene":
                sc = self.parse_scene()
                doc.scenes[sc.name] = sc
            else:
                raise ParseError(f"Declaração de topo desconhecida: {tok}")
        self.expect("}")
        return doc

    def parse_stage(self) -> Stage:
        st = Stage()
        self.expect("stage")
        self.expect("{")
        while self.peek() != "}":
            tok = self.pop()
            if tok == "size":
                st.width = self.expect_number()
                st.height = self.expect_number()
                st.viewbox = (st.viewbox[0], st.viewbox[1], st.width, st.height)
            elif tok == "viewbox":
                st.viewbox = (
                    self.expect_number(),
                    self.expect_number(),
                    self.expect_number(),
                    self.expect_number(),
                )
            elif tok == "background":
                st.background = self.parse_color_or_name()
            else:
                raise ParseError(f"Propriedade stage não suportada: {tok}")
        self.expect("}")
        return st

#    def parse_palette(self) -> Dict[str, str]:
#        out = {}
#        self.expect("palette")
#        self.expect("{")
#        while self.peek() != "}":
#            out[self.expect_ident()] = self.parse_color_or_name()
#        self.expect("}")
#        return out

    def parse_palette(self) -> Dict[str, str]:
        out = {}
        self.expect("palette")
        self.expect("{")
        while self.peek() != "}":
            name = self.expect_ident()
            color = self.parse_color_or_name()
            out[name] = color
        self.expect("}")
        return out

    def parse_fill(self) -> FillDef:
        mode = self.pop()
        if mode == "solid":
            return FillDef(kind="solid", color=self.parse_color_or_name())
        if mode == "linear":
            self.expect("(")
            x1 = self.expect_number(); y1 = self.expect_number()
            self.expect(",")
            x2 = self.expect_number(); y2 = self.expect_number()
            self.expect(")")
            self.expect("[")
            stops = []
            while self.peek() != "]":
                off = self.expect_percent_or_number()
                color = self.parse_color_or_name()
                stops.append(GradientStop(off, color))
                if self.peek() == ",":
                    self.pop()
            self.expect("]")
            return FillDef(kind="linear", x1=x1, y1=y1, x2=x2, y2=y2, stops=stops)
        if mode == "radial":
            self.expect("(")
            cx = self.expect_number(); cy = self.expect_number(); r = self.expect_number()
            self.expect(")")
            self.expect("[")
            stops = []
            while self.peek() != "]":
                off = self.expect_percent_or_number()
                color = self.parse_color_or_name()
                stops.append(GradientStop(off, color))
                if self.peek() == ",":
                    self.pop()
            self.expect("]")
            return FillDef(kind="radial", cx=cx, cy=cy, r=r, stops=stops)
        raise ParseError(f"Fill não suportado: {mode}")

    def parse_style(self) -> Style:
        self.expect("style")
        name = self.expect_string()
        st = Style(name=name)
        self.expect("{")
        while self.peek() != "}":
            tok = self.pop()
            if tok == "fill":
                st.fill = self.parse_fill()
            elif tok == "stroke":
                nxt = self.pop()
                if nxt == "none":
                    st.stroke = "none"
                    st.stroke_width = None
                else:
                    st.stroke = nxt
                    if self.peek() == "width":
                        self.pop()
                        st.stroke_width = self.expect_number()
            elif tok == "opacity":
                st.opacity = self.expect_number()
            else:
                raise ParseError(f"Style prop não suportada: {tok}")
        self.expect("}")
        return st

    def parse_primitive(self) -> Primitive:
        kind = self.pop()
        if kind == "rect":
            x = self.expect_number(); y = self.expect_number()
            w = self.expect_number(); h = self.expect_number()
            r = 0.0
            if self.peek() == "radius":
                self.pop(); r = self.expect_number()
            return Primitive(kind, {"x": x, "y": y, "w": w, "h": h, "r": r})
        if kind == "circle":
            cx = self.expect_number(); cy = self.expect_number(); r = self.expect_number()
            return Primitive(kind, {"cx": cx, "cy": cy, "r": r})
        if kind == "ellipse":
            cx = self.expect_number(); cy = self.expect_number()
            rx = self.expect_number(); ry = self.expect_number()
            return Primitive(kind, {"cx": cx, "cy": cy, "rx": rx, "ry": ry})
        if kind == "line":
            p1 = self.parse_point(); p2 = self.parse_point()
            return Primitive(kind, {"x1": p1[0], "y1": p1[1], "x2": p2[0], "y2": p2[1]})
        if kind in ("polygon", "polyline"):
            self.expect("[")
            pts = []
            while self.peek() != "]":
                pts.append(self.parse_point())
            self.expect("]")
            return Primitive(kind, {"points": pts})
        raise ParseError(f"Primitive não suportada: {kind}")

    def parse_path(self) -> List[str]:
        cmds = []
        self.expect("{")
        while self.peek() != "}":
            cmd = self.pop()
            if cmd == "M":
                p = self.parse_point()
                cmds.append(f"M {fnum(p[0])} {fnum(p[1])}")
            elif cmd == "L":
                p = self.parse_point()
                cmds.append(f"L {fnum(p[0])} {fnum(p[1])}")
            elif cmd == "H":
                x = self.expect_number()
                cmds.append(f"H {fnum(x)}")
            elif cmd == "V":
                y = self.expect_number()
                cmds.append(f"V {fnum(y)}")
            elif cmd == "Q":
                c = self.parse_point(); p = self.parse_point()
                cmds.append(f"Q {fnum(c[0])} {fnum(c[1])} {fnum(p[0])} {fnum(p[1])}")
            elif cmd == "C":
                c1 = self.parse_point(); c2 = self.parse_point(); p = self.parse_point()
                cmds.append(f"C {fnum(c1[0])} {fnum(c1[1])} {fnum(c2[0])} {fnum(c2[1])} {fnum(p[0])} {fnum(p[1])}")
            elif cmd == "S":
                c = self.parse_point(); p = self.parse_point()
                cmds.append(f"S {fnum(c[0])} {fnum(c[1])} {fnum(p[0])} {fnum(p[1])}")
            elif cmd == "A":
                rx = self.expect_number(); ry = self.expect_number(); rot = self.expect_number()
                large = int(self.expect_number()); sweep = int(self.expect_number()); p = self.parse_point()
                cmds.append(f"A {fnum(rx)} {fnum(ry)} {fnum(rot)} {large} {sweep} {fnum(p[0])} {fnum(p[1])}")
            elif cmd == "Z":
                cmds.append("Z")
            else:
                raise ParseError(f"Path cmd não suportado: {cmd}")
        self.expect("}")
        return cmds

    def parse_anchors_block(self) -> Dict[str, Tuple[float, float]]:
        out = {}
        self.expect("{")
        while self.peek() != "}":
            name = self.expect_ident()
            out[name] = (self.expect_number(), self.expect_number())
        self.expect("}")
        return out

    def parse_shape(self) -> ShapeDef:
        self.expect("shape")
        name = self.expect_string()
        sh = ShapeDef(name=name)
        self.expect("{")
        while self.peek() != "}":
            tok = self.pop()
            if tok == "bbox":
                sh.bbox = (self.expect_number(), self.expect_number())
            elif tok == "anchors":
                sh.anchors = self.parse_anchors_block()
            elif tok == "primitive":
                sh.primitive = self.parse_primitive()
            elif tok == "path":
                sh.path_cmds = self.parse_path()
            else:
                raise ParseError(f"Shape prop não suportada: {tok}")
        self.expect("}")
        if "center" not in sh.anchors:
            sh.anchors["center"] = (0.5, 0.5)
        return sh

    def parse_fit(self) -> FitSpec:
        fit = FitSpec()
        self.expect("{")
        while self.peek() != "}":
            tok = self.pop()
            if tok == "box":
                fit.box = (self.expect_number(), self.expect_number())
            else:
                raise ParseError(f"Fit prop não suportada: {tok}")
        self.expect("}")
        return fit

    def parse_attach(self) -> AttachSpec:
        child_anchor = None
        parent_anchor = None
        self.expect("{")
        while self.peek() != "}":
            tok = self.pop()
            if tok == "child-anchor":
                child_anchor = self.expect_ident()
            elif tok == "parent-anchor":
                parent_anchor = self.expect_ident()
            else:
                raise ParseError(f"Attach prop não suportada: {tok}")
        self.expect("}")
        if child_anchor is None or parent_anchor is None:
            raise ParseError("attach requer child-anchor e parent-anchor")
        return AttachSpec(child_anchor=child_anchor, parent_anchor=parent_anchor)

    def parse_use(self) -> UseDecl:
        self.expect("use")
        ref_name = self.expect_string()
        alias = None
        if self.peek() == "as":
            self.pop()
            alias = self.expect_string()
        u = UseDecl(ref_name=ref_name, alias=alias)
        self.expect("{")
        while self.peek() != "}":
            tok = self.pop()
            if tok == "style":
                u.style = self.expect_string()
            elif tok == "attach":
                u.attach = self.parse_attach()
            elif tok == "fit":
                u.fit = self.parse_fit()
            elif tok == "rotate":
                u.rotate = self.expect_number()
            elif tok == "pivot":
                u.pivot = self.expect_ident()
            else:
                raise ParseError(f"Use prop não suportada: {tok}")
        self.expect("}")
        return u

    def parse_repeat_radial(self) -> RepeatRadialDecl:
        self.expect("repeat")
        self.expect("radial")
        alias = self.expect_string()
        rr = RepeatRadialDecl(alias=alias, count=0, source="")
        self.expect("{")
        while self.peek() != "}":
            tok = self.pop()
            if tok == "count":
                rr.count = int(self.expect_number())
            elif tok == "source":
                rr.source = self.expect_string()
            elif tok == "style":
                rr.style = self.expect_string()
            elif tok == "origin":
                rr.origin = self.expect_ident()
            elif tok == "radius":
                rr.radius = self.expect_number()
            elif tok == "start-angle":
                rr.start_angle = self.expect_number()
            elif tok == "step-angle":
                rr.step_angle = self.expect_number()
            elif tok == "fit":
                rr.fit = self.parse_fit()
            elif tok == "child-anchor":
                rr.child_anchor = self.expect_ident()
            elif tok == "orient":
                rr.orient = self.pop()
            elif tok == "pivot":
                rr.pivot = self.expect_ident()
            else:
                raise ParseError(f"repeat radial prop não suportada: {tok}")
        self.expect("}")
        if rr.count <= 0:
            raise ParseError("repeat radial requer count > 0")
        if not rr.source:
            raise ParseError("repeat radial requer source")
        return rr

    def parse_object(self) -> ObjectDef:
        self.expect("object")
        name = self.expect_string()
        obj = ObjectDef(name=name)
        self.expect("{")
        while self.peek() != "}":
            tok = self.peek()
            if tok == "anchors":
                self.pop()
                obj.anchors = self.parse_anchors_block()
            elif tok == "use":
                obj.uses.append(self.parse_use())
            elif tok == "repeat":
                obj.repeats_radial.append(self.parse_repeat_radial())
            else:
                raise ParseError(f"Object stmt não suportado: {tok}")
        self.expect("}")
        if "center" not in obj.anchors:
            obj.anchors["center"] = (0.5, 0.5)
        return obj

    def parse_place(self) -> PlaceDecl:
        self.expect("place")
        ref_name = self.expect_string()
        alias = None
        if self.peek() == "as":
            self.pop()
            alias = self.expect_string()
        p = PlaceDecl(ref_name=ref_name, alias=alias)
        self.expect("{")
        while self.peek() != "}":
            tok = self.pop()
            if tok == "center":
                p.center = (self.expect_number(), self.expect_number())
            elif tok == "size":
                p.size = (self.expect_number(), self.expect_number())
            elif tok == "rotate":
                p.rotate = self.expect_number()
            elif tok == "style":
                p.style = self.expect_string()
            else:
                raise ParseError(f"Place prop não suportada: {tok}")
        self.expect("}")
        return p

    def parse_scene(self) -> SceneDef:
        self.expect("scene")
        name = self.expect_string()
        sc = SceneDef(name=name)
        self.expect("{")
        while self.peek() != "}":
            self.expect("layer")
            lname = self.expect_string()
            z = 0.0
            if self.peek() == "z":
                self.pop()
                z = self.expect_number()
            layer = LayerDecl(name=lname, z=z)
            self.expect("{")
            while self.peek() != "}":
                layer.places.append(self.parse_place())
            self.expect("}")
            sc.layers.append(layer)
        self.expect("}")
        return sc


@dataclass
class Box:
    x: float
    y: float
    w: float
    h: float
    rot: float = 0.0

@dataclass
class Frame:
    box: Box
    anchors: Dict[str, Tuple[float, float]]

@dataclass
class FlatNode:
    node_id: str
    shape: ShapeDef
    style: Optional[str]
    box: Box
    pivot_abs: Optional[Tuple[float, float]]
    z: float

class Compiler:
    def __init__(self, doc: Document):
        self.doc = doc
        self.gradient_defs: List[str] = []
        self.gradient_cache: Dict[str, str] = {}
        self.grad_counter = 0

    def resolve_color(self, s: Optional[str]) -> Optional[str]:
        if s is None:
            return None
        return self.doc.palette.get(s, s)

    def resolve_style(self, name: Optional[str]) -> Optional[Style]:
        if name is None:
            return None
        if name not in self.doc.styles:
            raise ValueError(f"Style não encontrado: {name}")
        st = deep_copy(self.doc.styles[name])
        if st.fill is not None:
            if st.fill.kind == "solid":
                st.fill.color = self.resolve_color(st.fill.color)
            else:
                for stop in st.fill.stops:
                    stop.color = self.resolve_color(stop.color)
        st.stroke = self.resolve_color(st.stroke)
        return st

    def style_attrs(self, style_name: Optional[str]) -> str:
        st = self.resolve_style(style_name)
        if st is None:
            return 'fill="none" stroke="black" stroke-width="1"'
        parts = []
        if st.fill is None:
            parts.append('fill="none"')
        elif st.fill.kind == "solid":
            parts.append(f'fill="{esc(st.fill.color or "none")}"')
        elif st.fill.kind in ("linear", "radial"):
            gid = self.ensure_gradient(st.fill)
            parts.append(f'fill="url(#{gid})"')
        if st.stroke is not None:
            parts.append(f'stroke="{esc(st.stroke)}"')
        if st.stroke_width is not None:
            parts.append(f'stroke-width="{fnum(st.stroke_width)}"')
        if st.opacity is not None:
            parts.append(f'opacity="{fnum(st.opacity)}"')
        return " ".join(parts)

    def ensure_gradient(self, fill: FillDef) -> str:
        key = self.gradient_key(fill)
        if key in self.gradient_cache:
            return self.gradient_cache[key]
        self.grad_counter += 1
        gid = f"gil3_grad_{self.grad_counter}"
        if fill.kind == "linear":
            lines = [f'<linearGradient id="{gid}" x1="{fnum(fill.x1)}" y1="{fnum(fill.y1)}" x2="{fnum(fill.x2)}" y2="{fnum(fill.y2)}">']
            for s in fill.stops:
                off = s.offset if s.offset.endswith("%") else f"{s.offset}%"
                lines.append(f'  <stop offset="{esc(off)}" stop-color="{esc(s.color)}"/>')
            lines.append("</linearGradient>")
        else:
            lines = [f'<radialGradient id="{gid}" cx="{fnum(fill.cx)}" cy="{fnum(fill.cy)}" r="{fnum(fill.r)}">']
            for s in fill.stops:
                off = s.offset if s.offset.endswith("%") else f"{s.offset}%"
                lines.append(f'  <stop offset="{esc(off)}" stop-color="{esc(s.color)}"/>')
            lines.append("</radialGradient>")
        self.gradient_defs.append("\n".join(lines))
        self.gradient_cache[key] = gid
        return gid

    def gradient_key(self, fill: FillDef) -> str:
        if fill.kind == "solid":
            return f"solid:{fill.color}"
        if fill.kind == "linear":
            return f"linear:{fill.x1},{fill.y1},{fill.x2},{fill.y2}:" + "|".join(f"{s.offset}:{s.color}" for s in fill.stops)
        return f"radial:{fill.cx},{fill.cy},{fill.r}:" + "|".join(f"{s.offset}:{s.color}" for s in fill.stops)

    def abs_anchor(self, box: Box, ax: float, ay: float) -> Tuple[float, float]:
        px = box.x + ax * box.w
        py = box.y + ay * box.h
        cx = box.x + box.w / 2.0
        cy = box.y + box.h / 2.0
        if abs(box.rot) < 1e-9:
            return (px, py)
        a = deg_to_rad(box.rot)
        dx = px - cx
        dy = py - cy
        rx = cx + dx * math.cos(a) - dy * math.sin(a)
        ry = cy + dx * math.sin(a) + dy * math.cos(a)
        return (rx, ry)

    def make_frame_for_object(self, obj: ObjectDef, box: Box) -> Frame:
        anchors = dict(obj.anchors)
        if "center" not in anchors:
            anchors["center"] = (0.5, 0.5)
        return Frame(box=box, anchors=anchors)

    def box_from_place(self, stage_box: Box, center: Tuple[float, float], size: Tuple[float, float], rotate: float) -> Box:
        w = stage_box.w * size[0]
        h = stage_box.h * size[1]
        cx = stage_box.x + center[0] * stage_box.w
        cy = stage_box.y + center[1] * stage_box.h
        return Box(x=cx - w / 2.0, y=cy - h / 2.0, w=w, h=h, rot=rotate)

    def child_box_attached(self, parent_frame: Frame, child_ref_anchors: Dict[str, Tuple[float, float]], attach: AttachSpec, fit: FitSpec, rotate: float) -> Tuple[Box, Optional[Tuple[float, float]]]:
        if fit.box is None:
            raise ValueError("attach requer fit { box ... }")
        if attach.parent_anchor not in parent_frame.anchors:
            raise ValueError(f"Anchor do pai não encontrado: {attach.parent_anchor}")
        if attach.child_anchor not in child_ref_anchors:
            raise ValueError(f"Anchor do filho não encontrado: {attach.child_anchor}")
        parent_anchor_rel = parent_frame.anchors[attach.parent_anchor]
        child_anchor_rel = child_ref_anchors[attach.child_anchor]
        w = parent_frame.box.w * fit.box[0]
        h = parent_frame.box.h * fit.box[1]
        target_abs = self.abs_anchor(parent_frame.box, parent_anchor_rel[0], parent_anchor_rel[1])
        x0 = target_abs[0] - child_anchor_rel[0] * w
        y0 = target_abs[1] - child_anchor_rel[1] * h
        box = Box(x=x0, y=y0, w=w, h=h, rot=rotate)
        return box, target_abs

    def child_box_polar(self, parent_frame: Frame, child_ref_anchors: Dict[str, Tuple[float, float]], origin_anchor: str, radius: float, angle: float, fit: FitSpec, child_anchor: str, orient: Optional[str]) -> Tuple[Box, float, Tuple[float, float]]:
        if fit.box is None:
            raise ValueError("polar/repeat radial requer fit { box ... }")
        if origin_anchor not in parent_frame.anchors:
            raise ValueError(f"Anchor de origem não encontrado: {origin_anchor}")
        if child_anchor not in child_ref_anchors:
            raise ValueError(f"Anchor do filho não encontrado: {child_anchor}")

        origin_rel = parent_frame.anchors[origin_anchor]
        origin_abs = self.abs_anchor(parent_frame.box, origin_rel[0], origin_rel[1])

        w = parent_frame.box.w * fit.box[0]
        h = parent_frame.box.h * fit.box[1]

        rr = min(parent_frame.box.w, parent_frame.box.h) * radius
        ar = deg_to_rad(angle)
        target_x = origin_abs[0] + math.cos(ar) * rr
        target_y = origin_abs[1] + math.sin(ar) * rr

        child_anchor_rel = child_ref_anchors[child_anchor]
        x0 = target_x - child_anchor_rel[0] * w
        y0 = target_y - child_anchor_rel[1] * h

        final_rot = angle + 90.0 if orient == "radial-out" else 0.0
        box = Box(x=x0, y=y0, w=w, h=h, rot=final_rot)

        pivot_abs = (target_x, target_y)
        return box, final_rot, pivot_abs

    def flatten_ref(self, ref_name: str, frame: Frame, inherited_style: Optional[str], prefix: str, zbase: float) -> List[FlatNode]:
        if ref_name in self.doc.shapes:
            shp = self.doc.shapes[ref_name]
            return [FlatNode(node_id=prefix, shape=shp, style=inherited_style, box=frame.box, pivot_abs=None, z=zbase)]

        if ref_name not in self.doc.objects:
            raise ValueError(f"Referência não encontrada: {ref_name}")

        obj = self.doc.objects[ref_name]
        obj_frame = self.make_frame_for_object(obj, frame.box)
        nodes: List[FlatNode] = []

        for idx, u in enumerate(obj.uses):
            child_name = u.alias or u.ref_name or f"item{idx}"
            child_prefix = f"{prefix}.{child_name}" if prefix else child_name
            child_style = u.style if u.style is not None else inherited_style

            if u.ref_name in self.doc.shapes:
                child_ref_anchors = dict(self.doc.shapes[u.ref_name].anchors)
            elif u.ref_name in self.doc.objects:
                child_ref_anchors = dict(self.doc.objects[u.ref_name].anchors)
            else:
                raise ValueError(f"Referência não encontrada: {u.ref_name}")
            if "center" not in child_ref_anchors:
                child_ref_anchors["center"] = (0.5, 0.5)

            if u.attach is None or u.fit is None:
                raise ValueError("Nesta versão, use requer attach e fit")
            child_box, pivot_abs = self.child_box_attached(obj_frame, child_ref_anchors, u.attach, u.fit, u.rotate)
            child_frame = Frame(box=child_box, anchors=child_ref_anchors)

            if u.ref_name in self.doc.shapes:
                nodes.append(FlatNode(node_id=child_prefix, shape=self.doc.shapes[u.ref_name], style=child_style, box=child_box, pivot_abs=pivot_abs if u.pivot else None, z=zbase))
            else:
                nodes.extend(self.flatten_ref(u.ref_name, child_frame, child_style, child_prefix, zbase))

        for rr in obj.repeats_radial:
            if rr.source in self.doc.shapes:
                child_ref_anchors = dict(self.doc.shapes[rr.source].anchors)
            elif rr.source in self.doc.objects:
                child_ref_anchors = dict(self.doc.objects[rr.source].anchors)
            else:
                raise ValueError(f"repeat radial source não encontrado: {rr.source}")
            if "center" not in child_ref_anchors:
                child_ref_anchors["center"] = (0.5, 0.5)

            for i in range(rr.count):
                angle = rr.start_angle + i * rr.step_angle
                child_box, _, pivot_abs = self.child_box_polar(
                    obj_frame, child_ref_anchors, rr.origin, rr.radius,
                    angle, rr.fit or FitSpec(box=(1.0, 1.0)), rr.child_anchor, rr.orient
                )
                child_prefix = f"{prefix}.{rr.alias}_{i}" if prefix else f"{rr.alias}_{i}"
                child_style = rr.style if rr.style is not None else inherited_style
                child_frame = Frame(box=child_box, anchors=child_ref_anchors)
                if rr.source in self.doc.shapes:
                    nodes.append(FlatNode(node_id=child_prefix, shape=self.doc.shapes[rr.source], style=child_style, box=child_box, pivot_abs=pivot_abs if rr.pivot else None, z=zbase))
                else:
                    nodes.extend(self.flatten_ref(rr.source, child_frame, child_style, child_prefix, zbase))
        return nodes

    def shape_svg(self, node: FlatNode) -> str:
        shape = node.shape
        style_attr = self.style_attrs(node.style)

        sx = node.box.w / shape.bbox[0] if shape.bbox[0] != 0 else 1.0
        sy = node.box.h / shape.bbox[1] if shape.bbox[1] != 0 else 1.0

        if node.pivot_abs is not None:
            pivot_local_x = node.pivot_abs[0] - node.box.x
            pivot_local_y = node.pivot_abs[1] - node.box.y
        else:
            pivot_local_x = node.box.w / 2.0
            pivot_local_y = node.box.h / 2.0

        outer_t = f'translate({fnum(node.box.x)} {fnum(node.box.y)})'
        rot_t = f'rotate({fnum(node.box.rot)} {fnum(pivot_local_x)} {fnum(pivot_local_y)})'
        scale_t = f'scale({fnum(sx)} {fnum(sy)})'

        if shape.primitive is not None:
            p = shape.primitive
            d = p.data
            if p.kind == "rect":
                inner = (
                    f'<rect x="{fnum(d["x"])}" y="{fnum(d["y"])}" '
                    f'width="{fnum(d["w"])}" height="{fnum(d["h"])}" '
                    f'rx="{fnum(d["r"])}" ry="{fnum(d["r"])}" {style_attr}/>'
                )
            elif p.kind == "circle":
                inner = f'<circle cx="{fnum(d["cx"])}" cy="{fnum(d["cy"])}" r="{fnum(d["r"])}" {style_attr}/>'
            elif p.kind == "ellipse":
                inner = (
                    f'<ellipse cx="{fnum(d["cx"])}" cy="{fnum(d["cy"])}" '
                    f'rx="{fnum(d["rx"])}" ry="{fnum(d["ry"])}" {style_attr}/>'
                )
            elif p.kind == "line":
                inner = (
                    f'<line x1="{fnum(d["x1"])}" y1="{fnum(d["y1"])}" '
                    f'x2="{fnum(d["x2"])}" y2="{fnum(d["y2"])}" {style_attr}/>'
                )
            elif p.kind in ("polygon", "polyline"):
                pts = " ".join(f"{fnum(x)},{fnum(y)}" for x, y in d["points"])
                inner = f'<{p.kind} points="{pts}" {style_attr}/>'
            else:
                raise ValueError(f"Primitive não suportada: {p.kind}")
        else:
            inner = f'<path d="{esc(" ".join(shape.path_cmds))}" {style_attr}/>'

        return (
            f'<g id="{esc(node.node_id)}" transform="{outer_t}">'
            f'<g transform="{rot_t}">'
            f'<g transform="{scale_t}">{inner}</g>'
            f'</g>'
            f'</g>'
        )

    def compile_scene(self, scene_name: str) -> str:
        if scene_name not in self.doc.scenes:
            raise ValueError(f"Scene não encontrada: {scene_name}")
        scene = self.doc.scenes[scene_name]
        st = self.doc.stage
        vb_x, vb_y, vb_w, vb_h = st.viewbox
        stage_box = Box(x=vb_x, y=vb_y, w=vb_w, h=vb_h, rot=0.0)

        rendered_layers = []
        for layer in scene.layers:
            nodes = []
            for p in layer.places:
                place_box = self.box_from_place(stage_box, p.center, p.size, p.rotate)
                place_frame = Frame(box=place_box, anchors={"center": (0.5, 0.5)})
                prefix = p.alias or p.ref_name
                nodes.extend(self.flatten_ref(p.ref_name, place_frame, p.style, prefix, layer.z))
            parts = [f'<g id="layer-{esc(layer.name)}">']
            for n in sorted(nodes, key=lambda x: x.z):
                parts.append(self.shape_svg(n))
            parts.append("</g>")
            rendered_layers.append((layer.z, "\n".join(parts)))

        _ = "\n".join(x for _, x in rendered_layers)

        lines = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{fnum(vb_x)} {fnum(vb_y)} {fnum(vb_w)} {fnum(vb_h)}" width="{fnum(st.width)}" height="{fnum(st.height)}" role="img" aria-label="{esc(scene_name)}">'
        ]
        if st.background is not None:
            bg = self.resolve_color(st.background)
            lines.append(f'  <rect x="{fnum(vb_x)}" y="{fnum(vb_y)}" width="{fnum(vb_w)}" height="{fnum(vb_h)}" fill="{esc(bg)}"/>')

        if self.gradient_defs:
            lines.append("  <defs>")
            for gd in self.gradient_defs:
                for ln in gd.splitlines():
                    lines.append("    " + ln)
            lines.append("  </defs>")

        for _, svg in sorted(rendered_layers, key=lambda t: t[0]):
            for ln in svg.splitlines():
                lines.append("  " + ln)

        lines.append("</svg>")
        return "\n".join(lines)


def parse_gil3(text: str) -> Document:
    return Parser(text).parse()

def compile_gil3_to_svg(text: str, scene_name: Optional[str] = None) -> str:
    doc = parse_gil3(text)
    if not doc.scenes:
        raise ValueError("Nenhuma scene foi definida.")
    scene = scene_name or next(iter(doc.scenes.keys()))
    return Compiler(doc).compile_scene(scene)

def compile_to_svg(text: str, scene_name: Optional[str] = None) -> str:
    return compile_gil3_to_svg(text, scene_name=scene_name)

def main() -> int:
    if len(sys.argv) < 2:
        print("Uso: python gil3_compiler_experimental.py arquivo.gil3 [saida.svg] [scene]", file=sys.stderr)
        return 1

    in_path = Path(sys.argv[1])
    if not in_path.exists():
        print(f"Arquivo não encontrado: {in_path}", file=sys.stderr)
        return 1

    out_path = Path(sys.argv[2]) if len(sys.argv) >= 3 else in_path.with_suffix(".svg")
    scene_name = sys.argv[3] if len(sys.argv) >= 4 else None

    try:
        text = in_path.read_text(encoding="utf-8")
        svg = compile_gil3_to_svg(text, scene_name=scene_name)
        out_path.write_text(svg, encoding="utf-8")
        print(f"SVG gerado em: {out_path}")
    except Exception as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 2
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

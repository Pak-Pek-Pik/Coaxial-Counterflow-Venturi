import math
import cadquery as cq

D_THROAT_EFF = 2.0
N_THROAT = 1.0

D_NEEDLE_OD = 1.0
D_NEEDLE_ID = 0.6
L_TIP = 1.6

D_VENTURI_IN = 4.0
D_VENTURI_OUT = 4.0
ANG_CONV_INCL = 21.0
ANG_DIV_INCL = 7.0

SECTION_FACTOR = 4.0
T_WALL_BODY = 1.0
T_WALL_HOUSING = 1.6

H_TURN = 2.6
T_END_B = 2.2
T_END_A = 2.2
R_TURN_MIN_K = 1.5

N_VANES = 3
T_VANE = 0.4
VANE_AXIAL_FRACTION = 0.55

L_STUB = 4.0
T_STUB = 1.0
D_INLET_BORE = 1.8

OUT_DIR = "output"

r_throat_eff = D_THROAT_EFF / 2.0
a_throat = math.pi * r_throat_eff**2

D_THROAT_PHYS = math.sqrt(D_THROAT_EFF**2 + D_NEEDLE_OD**2)
r_throat_phys = D_THROAT_PHYS / 2.0

r_vin = D_VENTURI_IN / 2.0
r_vout = D_VENTURI_OUT / 2.0

half_conv = math.radians(ANG_CONV_INCL / 2.0)
half_div = math.radians(ANG_DIV_INCL / 2.0)
l_conv = (r_vin - r_throat_phys) / math.tan(half_conv)
l_throat = N_THROAT * D_THROAT_EFF
l_div = (r_vout - r_throat_phys) / math.tan(half_div)

r_body_out = max(r_vin, r_vout) + T_WALL_BODY

a_annulus = SECTION_FACTOR * a_throat
r_hous_in = math.sqrt(r_body_out**2 + a_annulus / math.pi)
r_hous_out = r_hous_in + T_WALL_HOUSING
w_annulus = r_hous_in - r_body_out
r_turn = R_TURN_MIN_K * w_annulus
r_mean_ann = (r_hous_in + r_body_out) / 2.0

z_face_b = 0.0
z_turn_floor = T_END_B
z_body_bottom = z_turn_floor + H_TURN
z_throat_start = z_body_bottom + l_conv
z_throat_end = z_throat_start + l_throat
z_face_a = z_throat_end + l_div
l_total = z_face_a
z_throat_center = (z_throat_start + z_throat_end) / 2.0
z_ann_top = z_face_a - T_END_A

velocity_ratio_ann = a_annulus / a_throat
a_throat_phys_check = math.pi / 4.0 * (D_THROAT_PHYS**2 - D_NEEDLE_OD**2)

part = cq.Workplane("XY").circle(r_hous_out).extrude(l_total)

r1 = min(r_turn, 0.90 * H_TURN)
r2 = min(r_turn, 0.92 * (r_body_out - r_vin))


def arc_mid(corner, cx, cz):
    dx, dz = corner[0] - cx, corner[1] - cz
    n = math.hypot(dx, dz)
    r = n / math.sqrt(2)
    return (cx + dx / n * r, cz + dz / n * r)


c1 = (r_hous_in, z_turn_floor)
cen1 = (r_hous_in - r1, z_turn_floor + r1)
p2 = (r_hous_in - r1, z_turn_floor)
p1 = (r_hous_in, z_turn_floor + r1)
m1 = arc_mid(c1, *cen1)

c2 = (r_body_out, z_body_bottom)
cen2 = (r_body_out - r2, z_body_bottom + r2)
p3 = (r_body_out, z_body_bottom + r2)
p4 = (r_body_out - r2, z_body_bottom)
m2 = arc_mid(c2, *cen2)

fluid = (
    cq.Workplane("XZ")
    .moveTo(0.0, z_turn_floor)
    .lineTo(*p2)
    .threePointArc(m1, p1)
    .lineTo(r_hous_in, z_ann_top)
    .lineTo(r_body_out, z_ann_top)
    .lineTo(*p3)
    .threePointArc(m2, p4)
    .lineTo(r_vin, z_body_bottom)
    .lineTo(r_throat_phys, z_throat_start)
    .lineTo(r_throat_phys, z_throat_end)
    .lineTo(r_vout, z_face_a)
    .lineTo(0.0, z_face_a)
    .close()
    .revolve(360, (0, 0, 0), (0, 1, 0))
)

part = part.cut(fluid)

z_tip_base = z_throat_center - L_TIP
needle = (
    cq.Workplane("XY")
    .workplane(offset=z_face_b)
    .circle(D_NEEDLE_OD / 2.0)
    .extrude(z_tip_base)
)
tip = (
    cq.Workplane("XY")
    .workplane(offset=z_tip_base)
    .circle(D_NEEDLE_OD / 2.0)
    .workplane(offset=L_TIP)
    .circle(0.05)
    .loft(combine=True)
)
part = part.union(needle).union(tip)

air_bore = (
    cq.Workplane("XY")
    .workplane(offset=z_face_b - 0.1)
    .circle(D_NEEDLE_ID / 2.0)
    .extrude(z_tip_base + 0.4)
)
part = part.cut(air_bore)

z_vane_bot = z_body_bottom
h_vane = (z_ann_top - z_body_bottom) * VANE_AXIAL_FRACTION
for k in range(N_VANES):
    ang = 360.0 / N_VANES * k
    blade = (
        cq.Workplane("XY")
        .workplane(offset=z_vane_bot)
        .center(r_mean_ann, 0)
        .rect(w_annulus * 1.02, T_VANE)
        .extrude(h_vane)
        .rotate((0, 0, 0), (0, 0, 1), ang)
    )
    part = part.union(blade)

air_stub = (
    cq.Workplane("XY")
    .workplane(offset=z_face_b)
    .circle(D_NEEDLE_ID / 2.0 + T_STUB)
    .extrude(-L_STUB)
)
part = part.union(air_stub)
part = part.cut(
    cq.Workplane("XY")
    .workplane(offset=z_face_b + 0.1)
    .circle(D_NEEDLE_ID / 2.0)
    .extrude(-(L_STUB + 0.2))
)

out_stub = (
    cq.Workplane("XY")
    .workplane(offset=z_face_a)
    .circle(r_vout + T_STUB)
    .extrude(L_STUB)
)
part = part.union(out_stub)
part = part.cut(
    cq.Workplane("XY")
    .workplane(offset=z_face_a - 0.1)
    .circle(r_vout)
    .extrude(L_STUB + 0.2)
)

in_stub = (
    cq.Workplane("XY")
    .workplane(offset=z_face_a)
    .center(r_mean_ann, 0)
    .circle(D_INLET_BORE / 2.0 + T_STUB)
    .extrude(L_STUB)
)
part = part.union(in_stub)
in_bore = (
    cq.Workplane("XY")
    .workplane(offset=z_face_a + L_STUB + 0.1)
    .center(r_mean_ann, 0)
    .circle(D_INLET_BORE / 2.0)
    .extrude(-(L_STUB + 0.1 + T_END_A + 0.5))
)
part = part.cut(in_bore)

cq.exporters.export(part, OUT_DIR + "/venturi.step")
cq.exporters.export(part, OUT_DIR + "/venturi.stl", tolerance=0.01, angularTolerance=0.1)
try:
    cq.exporters.export(part, OUT_DIR + "/venturi.iges", exportType="IGES")
except Exception as e:
    print("  [info] IGES export skipped:", e)

try:
    cq.exporters.export(
        part,
        OUT_DIR + "/preview.svg",
        opt={
            "projectionDir": (1, -1, 0.6),
            "showAxes": False,
            "strokeWidth": 0.25,
            "width": 900,
            "height": 700,
        },
    )
except Exception as e:
    print("  [info] SVG export skipped:", e)

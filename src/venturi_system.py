# -*- coding: utf-8 -*-
"""
=============================================================================
 SYSTEME 3 - VENTURI COAXIAL A CONTRE-COURANT AVEC INJECTION D'AIR INVERSEE
 Modele CAO 3D parametrique (CadQuery / OpenCASCADE)
-----------------------------------------------------------------------------
 PRINCIPE : decouplage RETOURNEMENT / ACCELERATION
   - L'eau entre par un orifice EXCENTRE (Face A) dans un espace ANNULAIRE
     externe, parcourt la peripherie, effectue son demi-tour
     a 180 deg AU FOND a basse vitesse, puis s'accelere dans le Venturi
     INTERNE rectiligne et ressort
     par le CENTRE de la Face A.
   - L'air est admis par le CENTRE de la Face B (fond borgne de l'eau) via une
     aiguille/canule coaxiale fixe traversant la zone de retournement et
     debouchant pile au col (zone de depression maximale).
-----------------------------------------------------------------------------
 Sortie : .STEP (AP214) + .STL + .IGES
=============================================================================
"""

import math
import cadquery as cq

# ============================================================================
#  1.  PARAMETRES PRIMAIRES  (modifier ici)
# ============================================================================

# --- Col (organe deprimogene) ---------------------------------------------
D_COL_EFF      = 2.0     # [mm] diametre de passage d'EAU EFFECTIF au col
N_COL          = 1.0     # longueur cylindrique du col = N_COL * D_COL_EFF (ISO)

# --- Aiguille / canule d'air centrale -------------------------------------
D_AIG_EXT      = 1.0     # [mm] diametre exterieur de l'aiguille d'air
D_AIG_INT      = 0.6     # [mm] alesage interne (passage d'air)
L_OGIVE        = 1.6     # [mm] longueur de l'ogive effilee (pointe au col)

# --- Tube Venturi interne (conforme ISO 5167) -----------------------------
D_VENTURI_IN   = 4.0     # [mm] diametre amont du convergent (grande base, cote B)
D_VENTURI_OUT  = 4.0     # [mm] diametre aval du divergent (refoulement, Face A)
ANG_CONV_INCL  = 21.0    # [deg] angle INCLUS du convergent (21 +/- 1)
ANG_DIV_INCL   = 7.0     # [deg] angle INCLUS du divergent (7, anti-decollement)

# --- Espace annulaire externe (eau) ---------------------------------------
FACT_SECTION   = 4.0     # section annulaire mini = FACT_SECTION * section col
EP_PAROI_VB    = 1.0     # [mm] epaisseur de paroi du corps Venturi interne
EP_PAROI_HOUS  = 1.6     # [mm] epaisseur de paroi du carter externe

# --- Zone de retournement (fond, cote B) ----------------------------------
H_RETOUR       = 2.6     # [mm] hauteur axiale du plenum de retournement 180 deg
EP_FOND_B      = 2.2     # [mm] epaisseur du fond borgne (Face B)
EP_FOND_A      = 2.2     # [mm] epaisseur du fond avant (cape l'anneau, Face A)
R_TURN_MIN_K   = 1.5     # rayon de courbure retournement >= K * largeur anneau

# --- Ailettes de guidage anti-Dean (3 a 120 deg) --------------------------
N_AILETTES     = 3
EP_AILETTE     = 0.4     # [mm] epaisseur des ailettes minces
FRAC_AIL_AX    = 0.55    # fraction de la hauteur d'anneau couverte par l'ailette

# --- Raccords (tubulures de connexion) ------------------------------------
L_STUB         = 4.0     # [mm] longueur des embouts de raccordement
EP_STUB        = 1.0     # [mm] epaisseur de paroi des embouts
D_INLET_BORE   = 1.8     # [mm] alesage de l'orifice d'entree d'eau excentre

# ============================================================================
#  2.  GEOMETRIE DERIVEE  (calculs automatiques)
# ============================================================================

R_col_eff   = D_COL_EFF / 2.0
A_col       = math.pi * R_col_eff**2                      # section utile col

# Col PHYSIQUE : tient compte de l'encombrement de l'aiguille
#   A_col = pi/4 (D_col_phys^2 - D_aig^2)  =>  D_col_phys = sqrt(D_col_eff^2 + D_aig^2)
D_COL_PHYS  = math.sqrt(D_COL_EFF**2 + D_AIG_EXT**2)
R_col_phys  = D_COL_PHYS / 2.0

R_vin       = D_VENTURI_IN  / 2.0
R_vout      = D_VENTURI_OUT / 2.0

# Longueurs des troncs coniques (a partir des demi-angles)
half_conv   = math.radians(ANG_CONV_INCL / 2.0)
half_div    = math.radians(ANG_DIV_INCL  / 2.0)
L_CONV      = (R_vin  - R_col_phys) / math.tan(half_conv)
L_THROAT    = N_COL * D_COL_EFF
L_DIV       = (R_vout - R_col_phys) / math.tan(half_div)

# Corps Venturi interne : rayon exterieur
R_vb_out    = max(R_vin, R_vout) + EP_PAROI_VB

# Espace annulaire : section = FACT_SECTION * A_col
#   pi (R_hous_in^2 - R_vb_out^2) = FACT_SECTION * A_col
A_annulaire = FACT_SECTION * A_col
R_hous_in   = math.sqrt(R_vb_out**2 + A_annulaire / math.pi)
R_hous_out  = R_hous_in + EP_PAROI_HOUS
W_ANNEAU    = R_hous_in - R_vb_out                        # largeur de l'anneau
R_TURN      = R_TURN_MIN_K * W_ANNEAU                     # rayon retournement requis
R_mean_ann  = (R_hous_in + R_vb_out) / 2.0                # rayon moyen anneau

# Stations axiales (z = 0 Face B ; z croissant vers Face A)
z_face_B       = 0.0
z_turn_floor   = EP_FOND_B                                # face interne du fond B
z_vb_bottom    = z_turn_floor + H_RETOUR                  # base du corps Venturi (entree convergent)
z_throat_start = z_vb_bottom + L_CONV
z_throat_end   = z_throat_start + L_THROAT
z_face_A       = z_throat_end + L_DIV                     # sortie divergent = Face A
L_TOTAL        = z_face_A
z_col_center   = (z_throat_start + z_throat_end) / 2.0
z_ann_top      = z_face_A - EP_FOND_A                     # sous-face du fond avant (cape anneau)

# Verifications de conformite (affichees a l'execution)
v_ratio_ann = A_annulaire / A_col                         # v_col/v_ann = ce rapport
A_col_phys_check = math.pi/4.0 * (D_COL_PHYS**2 - D_AIG_EXT**2)

# ============================================================================
#  3.  CONSTRUCTION DU SOLIDE
# ============================================================================

# ---- 3.1  Carter externe plein (cylindre enveloppe) ----------------------
part = cq.Workplane("XY").circle(R_hous_out).extrude(L_TOTAL)

# ---- 3.2  Domaine fluide (eau) : profil meridien revolu ------------------
# Le passage d'eau (anneau + retournement 180 + Venturi interne) est decrit
# par un profil meridien (r, z) revolu de 360 deg autour de l'axe.
# Les deux coins du retournement au fond recoivent un arrondi (arc) de rayon
# R_TURN >= 1,5 x largeur d'anneau, integre DIRECTEMENT au profil :
#   - coin exterieur (carter / fond B)
#   - coin interieur (base du corps Venturi) -> tangent a l'entree du convergent
r1 = min(R_TURN, 0.90 * H_RETOUR)                    # arrondi coin exterieur
r2 = min(R_TURN, 0.92 * (R_vb_out - R_vin))          # arrondi coin interieur (Venturi)

def arc_mid(corner, cx, cz):
    """Point milieu d'un arc de raccordement de 90 deg (pour threePointArc)."""
    dx, dz = corner[0] - cx, corner[1] - cz
    n = math.hypot(dx, dz)
    r = n / math.sqrt(2)            # = rayon (corner a distance r*sqrt2 du centre)
    return (cx + dx / n * r, cz + dz / n * r)

# Coin exterieur C1 = (R_hous_in, z_turn_floor)
c1   = (R_hous_in, z_turn_floor)
cen1 = (R_hous_in - r1, z_turn_floor + r1)
P2   = (R_hous_in - r1, z_turn_floor)          # tangent sur le sol
P1   = (R_hous_in,      z_turn_floor + r1)     # tangent sur la paroi carter
M1   = arc_mid(c1, *cen1)

# Coin interieur C2 = (R_vb_out, z_vb_bottom)
c2   = (R_vb_out, z_vb_bottom)
cen2 = (R_vb_out - r2, z_vb_bottom + r2)
P3   = (R_vb_out,      z_vb_bottom + r2)        # tangent sur la paroi du corps
P4   = (R_vb_out - r2, z_vb_bottom)             # tangent sur la face inf. du corps
M2   = arc_mid(c2, *cen2)

fluid = (
    cq.Workplane("XZ")
    .moveTo(0.0, z_turn_floor)            # axe, sol du retournement
    .lineTo(*P2)                          # sol vers le coin exterieur
    .threePointArc(M1, P1)               # arrondi coin exterieur (R_TURN)
    .lineTo(R_hous_in, z_ann_top)        # remontee paroi exterieure anneau
    .lineTo(R_vb_out,  z_ann_top)        # sous-face fond avant (cape l'anneau)
    .lineTo(*P3)                          # descente paroi ext. corps Venturi
    .threePointArc(M2, P4)               # arrondi coin interieur (-> tangent convergent)
    .lineTo(R_vin,      z_vb_bottom)     # face inf. corps -> entree convergent
    .lineTo(R_col_phys, z_throat_start)  # convergent 21 deg
    .lineTo(R_col_phys, z_throat_end)    # col cylindrique (2 mm effectif)
    .lineTo(R_vout,     z_face_A)        # divergent 7 deg -> Face A
    .lineTo(0.0,        z_face_A)        # bouche du divergent -> axe
    .close()
    .revolve(360, (0, 0, 0), (0, 1, 0))
)

part = part.cut(fluid)

# ---- 3.3  Aiguille d'air coaxiale (canule + ogive) -----------------------
# Tige cylindrique de la Face B jusqu'au debut de l'ogive...
z_ogive_base = z_col_center - L_OGIVE
needle = (
    cq.Workplane("XY")
    .workplane(offset=z_face_B)
    .circle(D_AIG_EXT / 2.0)
    .extrude(z_ogive_base)
)
# ... puis ogive effilee (cone) se terminant pile au centre du col.
ogive = (
    cq.Workplane("XY")
    .workplane(offset=z_ogive_base)
    .circle(D_AIG_EXT / 2.0)
    .workplane(offset=L_OGIVE)
    .circle(0.05)                    # quasi-pointe (0.1 mm) pour robustesse maillage
    .loft(combine=True)
)
part = part.union(needle).union(ogive)

# Alesage d'air : de la Face B jusqu'a la base de l'ogive (debouche au col)
air_bore = (
    cq.Workplane("XY")
    .workplane(offset=z_face_B - 0.1)
    .circle(D_AIG_INT / 2.0)
    .extrude(z_ogive_base + 0.4)     # debouche juste avant la pointe
)
part = part.cut(air_bore)

# ---- 3.4  Ailettes de guidage anti-Dean (N a 120 deg) --------------------
z_ail_bot = z_vb_bottom
h_ail     = (z_ann_top - z_vb_bottom) * FRAC_AIL_AX
for k in range(N_AILETTES):
    ang = 360.0 / N_AILETTES * k
    blade = (
        cq.Workplane("XY")
        .workplane(offset=z_ail_bot)
        .center(R_mean_ann, 0)
        .rect(W_ANNEAU * 1.02, EP_AILETTE)
        .extrude(h_ail)
        .rotate((0, 0, 0), (0, 0, 1), ang)
    )
    part = part.union(blade)

# ---- 3.5  Raccords (embouts de connexion) --------------------------------
# (a) Embout d'air centrale, Face B (protrusion z < 0)
air_stub = (
    cq.Workplane("XY").workplane(offset=z_face_B)
    .circle(D_AIG_INT / 2.0 + EP_STUB).extrude(-L_STUB)
)
part = part.union(air_stub)
part = part.cut(
    cq.Workplane("XY").workplane(offset=z_face_B + 0.1)
    .circle(D_AIG_INT / 2.0).extrude(-(L_STUB + 0.2))
)

# (b) Embout de refoulement d'eau, CENTRE Face A (protrusion z > L_TOTAL)
out_stub = (
    cq.Workplane("XY").workplane(offset=z_face_A)
    .circle(R_vout + EP_STUB).extrude(L_STUB)
)
part = part.union(out_stub)
part = part.cut(
    cq.Workplane("XY").workplane(offset=z_face_A - 0.1)
    .circle(R_vout).extrude(L_STUB + 0.2)
)

# (c) Embout d'entree d'eau EXCENTRE, Face A (raccorde l'anneau)
in_stub = (
    cq.Workplane("XY").workplane(offset=z_face_A)
    .center(R_mean_ann, 0).circle(D_INLET_BORE / 2.0 + EP_STUB).extrude(L_STUB)
)
part = part.union(in_stub)
# percage de l'entree : du sommet de l'embout jusque dans l'anneau
in_bore = (
    cq.Workplane("XY").workplane(offset=z_face_A + L_STUB + 0.1)
    .center(R_mean_ann, 0).circle(D_INLET_BORE / 2.0)
    .extrude(-(L_STUB + 0.1 + EP_FOND_A + 0.5))
)
part = part.cut(in_bore)

# ============================================================================
#  4.  EXPORT
# ============================================================================
out_dir = "/Users/galaadpaquin/Desktop/VENTURI/sortie"
cq.exporters.export(part, out_dir + "/systeme3_venturi.step")
cq.exporters.export(part, out_dir + "/systeme3_venturi.stl",
                    tolerance=0.01, angularTolerance=0.1)
try:
    cq.exporters.export(part, out_dir + "/systeme3_venturi.iges", exportType="IGES")
except Exception as e:
    print("  [info] export IGES ignore :", e)

# Vue isometrique SVG (controle visuel rapide)
try:
    cq.exporters.export(
        part, out_dir + "/apercu.svg",
        opt={"projectionDir": (1, -1, 0.6), "showAxes": False,
             "strokeWidth": 0.25, "width": 900, "height": 700},
    )
except Exception as e:
    print("  [info] export SVG ignore :", e)



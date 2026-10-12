# Preliminary structural analysis

The elastic analysis is a limited, linear, static estimate for each run's BASE geometry. It is not a strength approval or a fatigue calculation. Alternatives without FEM retain an explicit not-calculated status.

## Materials and units

The demonstrated BASE uses a public reference for UNS C95800 nickel-aluminum bronze: density 7,640 kg/m³, elastic modulus approximately 113.7635 GPa and Poisson ratio 0.32. The modulus converts the [Copper Development Association](https://alloys.copper.org/alloy/C95800) value of 16,500 ksi to SI. No yield allowable is assigned to an unspecified manufacturing condition.

Mass is solid CAD volume multiplied by the selected reference density. It excludes porosity, coatings, attachments and manufacturing tolerances. The material configuration separates known reference values from missing properties. A material with missing modulus or Poisson ratio does not receive an elastic estimate. No lot certificates, fatigue curves in seawater, corrosion allowances or class allowables are provided.

FreeCAD geometry is generated in millimeters; public volumes use m³ and the meshing import explicitly targets meters. Recorded bounding boxes and volume checks guard the exchange.

## Mesh verification

[Gmsh](https://gmsh.info/doc/texinfo/gmsh.html) imports the reopened BASE STEP and creates linear tetrahedral MSH 2.2 ASCII meshes with characteristic maximum lengths `D/30` and `D/45`. Checks count inverted and degenerate tetrahedra, non-manifold internal faces and volume error against the CAD.

The normalized tetrahedral mean ratio is

```text
q = 12*(3*V)^(2/3) / sum(edge_length^2)
```

It is one for an equilateral tetrahedron and zero at zero volume. It is a geometric quality indicator, not a solver error estimate. The original acceptance criteria were volume discrepancy at most 5%, no inversions or degeneracies and no non-manifold faces.

The baseline meshes contain 8,996 and 19,055 tetrahedra. Their volume discrepancies are approximately 0.930% and 0.485%. Each retains three tetrahedra below mean-ratio quality 0.05. Two mesh sizes establish neither FEM stress convergence nor CFD independence.

## Analytical solver benchmark

[CalculiX](https://www.calculix.de/) 2.22 solves a synthetic 0.1 m cube using one C3D8 element, modulus 200 GPa and Poisson ratio zero. A 100 N uniaxial load gives:

```text
stress = F/A = 10,000 Pa
extension = F*L/(A*E) = 5e-9 m
reaction = -100 N
```

The displacement, eight integration-point stresses and reaction are checked with relative tolerance `1e-5`; the solver output file must exist. The recorded benchmark passed. This verifies invocation, units, output reading and a simple analytical response, not a propeller's structural performance.

## Propeller loading and restraints

The shaft axis is Z. Hub-region nodes have fixed XYZ translation, representing an ideal rigid hub. The propeller uses linear isotropic C3D4 elements.

BEM provides thrust and torque for each annulus of the entire propeller. Surface-node weights derive from incident triangle areas. Axial and tangential equivalent forces are distributed to conserve annular thrust and torque and control spurious transverse resultants. A covariance correction is checked for singularity and negative axial weights. This is a conservative resultant transfer; it is not a resolved pressure field on blade pressure and suction faces.

Centrifugal force is based on undeformed geometry and node masses obtained by distributing each tetrahedron's density-times-volume equally to its four nodes. Geometric stiffness and rotating dynamics are absent. Actual CalculiX reactions are compared with applied force and moment, with a `1e-3` relative acceptance tolerance.

For the 900 RPM baseline, recorded maximum displacement is approximately **35.42 µm** and integration-point von Mises stress **16.93 MPa**. Relative force and moment residuals are about `2.02e-4` and `2.81e-6`. Display precision is not physical uncertainty.

## Required work before structural decisions

The generated geometry lacks a verified root fillet, manufacturing trailing-edge thickness and actual shaft connection details. The ideal hub support and linear tetrahedra can make local peaks dependent on mesh and restraint assumptions. The present calculation omits pressure-field validation, stress convergence, certified material allowables, manufacturing effects, fatigue, corrosion and cavitation damage.

No factor of safety, endurance life, fracture criterion, classification compliance or permission to fabricate follows from these results. The ranked diameter-study candidate has no elastic solution and cannot be described as the structurally preferred design.

Future work should first define material condition, manufacturing route and real supports, then improve geometry and loading, converge the solution and apply appropriate failure and service criteria.

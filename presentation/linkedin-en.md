# LinkedIn draft — English

Status: proposed text for author review. Not posted. The repository destination is identified; verify its public contents before posting this message.

---

I developed **CantaX Propeller Lab**, a local engineering demonstrator connecting Excel, FreeCAD, MATLAB/Simulink, Gmsh and CalculiX through custom automation software.

The goal is to make a parameter change reproducible: inputs → CAD geometry → preliminary hydrodynamic estimates → shaft dynamics → preliminary elasticity → results and a technical report. Octave and Scilab independently check definitions and units.

Four historical workflows and a publication regression generated 65 verified CAD solids. Changing from 900 to 1,000 RPM updated thrust, torque and power while preserving geometric volume. A five-blade, P/D = 0.85 case regenerated geometry and calculations. A further study compared 13 configurations.

One useful outcome was a motor torque limit in the higher-speed scenario. The workflow retains that unfavorable result instead of forcing a successful operating point.

The implementation was developed with AI assistance and recorded numerical checks. The author's human review before communication is distinct from independent physical validation. This is preliminary engineering work: not validated 3D CFD, certified naval software or a finished commercial product.

I am sharing the source, examples, documentation and explicit limitations to support critical technical review.

Repository: [CantaX Propeller Lab](https://github.com/aaronexposito0-creator/cantax-propeller-lab)

#Engineering #Automation #CAD #Simulation #SoftwareDevelopment

---

The author should review the repository, figures, rights and media before posting. Preserve the pending-review status if that review has not happened. Do not claim independent human validation of loads or design performance.

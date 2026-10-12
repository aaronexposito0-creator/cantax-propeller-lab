# Borrador de LinkedIn — español

Estado: propuesta para revisión del autor. No publicada. El destino del repositorio está identificado; comprobar sus contenidos públicos antes de publicar este mensaje.

---

He desarrollado **CantaX Propeller Lab**, un demostrador local de ingeniería que conecta Excel, FreeCAD, MATLAB/Simulink, Gmsh y CalculiX mediante software propio de automatización.

La idea es convertir un cambio de parámetros en un proceso reproducible: entradas → geometría CAD → estimaciones hidrodinámicas → dinámica del eje → análisis elástico preliminar → resultados e informe técnico. Octave y Scilab contrastan definiciones y unidades.

Cuatro pruebas históricas y una regresión de publicación generaron 65 sólidos CAD verificados. Cambiar de 900 a 1000 RPM actualizó empuje, par y potencia sin alterar el volumen. Cambiar a cinco palas y P/D = 0,85 regeneró la geometría y los cálculos. Un estudio adicional comparó 13 configuraciones.

Un resultado especialmente útil: el escenario de mayor velocidad encontró un límite de par del motor. La automatización conserva ese resultado desfavorable, en lugar de forzar una conclusión.

La implementación se desarrolló con asistencia de IA y comprobaciones numéricas registradas. La revisión humana del autor antes de comunicarlo no equivale a validación física independiente. Esta es una herramienta preliminar: sin CFD 3D validado, certificación naval ni madurez de producto comercial.

Comparto código, ejemplos, documentación y las limitaciones para facilitar una revisión técnica crítica.

Repositorio: [CantaX Propeller Lab](https://github.com/aaronexposito0-creator/cantax-propeller-lab)

#Ingeniería #Automatización #CAD #Simulación #DesarrolloDeSoftware

---

Antes de publicar, el autor debe revisar repositorio, cifras, derechos e imágenes. Si esa revisión aún no se ha realizado, conservar expresamente su condición pendiente. No afirmar una validación humana independiente de las cargas o del diseño.

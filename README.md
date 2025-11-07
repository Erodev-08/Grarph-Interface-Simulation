# Grafos GUI

Aplicación de escritorio en Python para crear, visualizar y analizar grafos de manera interactiva.

Este repositorio contiene el script principal `Grafos-Graphic-User-Interface.py`, una interfaz rica basada en PyQt5 que permite:

- Crear y editar nodos y aristas de forma visual.
- Ejecutar y visualizar algoritmos clásicos (BFS, DFS, Dijkstra, Kruskal, Prim, etc.).
- Exportar el grafo en varios formatos (GraphML, DOT, matriz de adyacencia, lista de aristas, PNG/SVG).
- Preferencias de visualización y opciones de exportación.
- (Opcional) Vista 3D cuando Ursina está instalado.

---

## Requisitos

- Python 3.8 o superior
- PyQt5

Opcionales (habilitan funciones adicionales):
- networkx — para análisis y algunos layouts/algoritmos
- ursina — para la vista 3D
- PyQt5.QtSvg — para exportar SVG (normalmente incluido con PyQt5)

No crearé entornos virtuales aquí; las instrucciones ofrecen instalación directa. Si prefieres aislar dependencias, puedes usar virtualenv o conda localmente.

## Instalación (sin entornos virtuales)

Instala las dependencias globalmente o por usuario. En Windows PowerShell (ejecutar como usuario normal):

```powershell
# Instalar PyQt5 (requerido)
python -m pip install --user PyQt5

# (Opcional) Instalar NetworkX para análisis adicionales
python -m pip install --user networkx

# (Opcional) Instalar Ursina para la vista 3D
python -m pip install --user ursina
```

Si prefieres instalar para todo el sistema (requiere permisos de administrador), omite `--user`.

## Ejecución

Desde PowerShell, en la carpeta del proyecto ejecuta:

```powershell
python "Grafos-Graphic-User-Interface.py"
```

Si tienes varias versiones de Python, usa `py -3` o la ruta al ejecutable adecuado.

## Uso básico

- Arrastra o haz clic en el canvas para añadir nodos.
- Selecciona nodos y arrástralos para moverlos. Mantén pulsada la tecla Shift (o usa la barra de herramientas) para seleccionar múltiples.
- Usa el menú `Algoritmos` para ejecutar BFS, DFS, Dijkstra, Kruskal y otros. Las animaciones y resaltados se pueden controlar desde las Preferencias.
- Exporta grafos usando los menús `Archivo > Exportar` para crear archivos GraphML, DOT, PNG o SVG.

## Opciones y características avanzadas

- Preferencias: tema claro/oscuro, tamaño de fuente, rejilla, snap a rejilla, colores predeterminados, velocidad de animación.
- 3D: si `ursina` está instalado, puedes abrir la vista 3D desde el menú y obtener una representación espacial del grafo.
- Análisis: con `networkx` disponible, se habilitan análisis de centralidad, componentes, detección de comunidades y más.

## Solución de problemas

- Error `ModuleNotFoundError: No module named 'PyQt5'`: instala PyQt5 con pip (`python -m pip install --user PyQt5`).
- Problemas con `ursina` o `networkx`: son opcionales; la aplicación funciona sin ellos, pero ciertas funcionalidades quedan deshabilitadas.
- Problemas de escala DPI en Windows: la aplicación intenta manejar DPI altos; si hay problemas visuales, prueba a ajustar la escala de la pantalla en la configuración de Windows.

## Contribuir

Si quieres contribuir, abre un issue o un pull request con cambios pequeños y descriptivos. Mantén el estilo de código y agrega pruebas mínimas si introduces lógica nueva o cambios en algoritmos.

## Licencia

Licencia MIT — revisa o añade un archivo `LICENSE` si quieres declarar explícitamente la licencia.

## Contacto

Si tienes dudas o quieres funciones nuevas, crea un issue en el repositorio o contacta al mantenedor.

---

_Generado automáticamente para el archivo `Grafos-Graphic-User-Interface.py`. Si quieres que incluya instrucciones para crear un entorno virtual o un `requirements.txt`, dímelo y lo añado._

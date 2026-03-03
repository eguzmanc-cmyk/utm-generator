# Stack Tecnológico del Proyecto: Generador de UTMs Automático

Este documento detalla las tecnologías y librerías clave que se utilizarán en el desarrollo del Generador de UTMs Automático, junto con una breve justificación de su elección.

## 1. Frontend & Lógica de Aplicación: Streamlit

*   **Enlace:** [Streamlit](https://streamlit.io/)
*   **Justificación:** Streamlit es un framework de Python de código abierto que permite crear aplicaciones web interactivas de forma rápida y sencilla con solo unas pocas líneas de código. Es ideal para prototipos, herramientas internas y aplicaciones de datos, lo que lo hace perfecto para una aplicación de generación de UTMs. Su facilidad de uso y la capacidad de desplegarse gratuitamente en su nube son factores clave.

## 2. Base de Datos & Autenticación: Supabase

*   **Enlace:** [Supabase](https://supabase.io/)
*   **Justificación:** Supabase es una alternativa de código abierto a Firebase que proporciona una base de datos PostgreSQL, autenticación, APIs instantáneas y almacenamiento. Se eligió por su facilidad de integración con Python, su modelo de autenticación listo para usar y su generoso plan gratuito, que es adecuado para este proyecto. Permite gestionar usuarios y sus datos de forma eficiente.

## 3. Lenguaje de Programación: Python

*   **Enlace:** [Python](https://www.python.org/)
*   **Justificación:** Python es el lenguaje de programación principal para este proyecto debido a su legibilidad, vasta colección de librerías y su fuerte ecosistema con Streamlit y Supabase. Es un lenguaje versátil que permite un desarrollo rápido y eficiente.

## 4. Gestión de Dependencias: `pip` y `requirements.txt`

*   **Enlace:** [pip](https://pip.pypa.io/en/stable/)
*   **Justificación:** `pip` es el gestor de paquetes estándar de Python. Se utilizará para instalar y gestionar las librerías necesarias para el proyecto. El archivo `requirements.txt` contendrá una lista de todas las dependencias para asegurar un entorno de desarrollo y despliegue consistente.

## 5. Control de Versiones: Git

*   **Enlace:** [Git](https://git-scm.com/)
*   **Justificación:** Git es el sistema de control de versiones distribuido más utilizado. Permitirá el seguimiento de cambios en el código, la colaboración y la gestión de diferentes versiones del proyecto.
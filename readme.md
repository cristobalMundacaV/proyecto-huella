# Proyecto Huella

Plataforma para medir, analizar y optimizar huella de carbono empresarial con:

- API backend en Django + DRF
- Frontend en React + Vite
- Pipeline de datos en Python
- Dashboard alternativo en Streamlit

## Requisitos

- Python 3.13+
- Node.js 20+
- npm 10+

## Configuracion

1. Crear entorno virtual e instalar dependencias Python:

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

2. Instalar dependencias frontend:

```bash
cd frontend
npm install
cd ..
```

3. Crear archivo de entorno:

```bash
copy env.example .env
```

## Ejecutar el proyecto

1. Levantar backend:

```bash
cd backend
python manage.py runserver
```

2. Levantar frontend (en otra terminal):

```bash
cd frontend
npm run dev
```

3. Opcional: dashboard Streamlit:

```bash
streamlit run app/dashboard/streamlit_app.py
```

## Variables de entorno

Ver `env.example`.

Variables principales:

- `DJANGO_SECRET_KEY`: clave secreta de Django.
- `DJANGO_DEBUG`: `True` en desarrollo, `False` en produccion.
- `DJANGO_ALLOWED_HOSTS`: hosts separados por coma.
- `CORS_ALLOW_ALL_ORIGINS`: `True` solo en desarrollo.
- `CORS_ALLOWED_ORIGINS`: lista separada por coma de origenes permitidos.
- `CSRF_TRUSTED_ORIGINS`: lista separada por coma para CSRF en despliegue.
- `OPENAI_API_KEY`: clave para asesor IA.
- `VITE_API_URL`: URL base del frontend para consumir la API.

## Pruebas

```bash
python -m unittest discover -s tests -p "test_*.py"
```

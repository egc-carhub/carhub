# Usamos Python 3.11 como base
FROM python:3.11-slim

# Directorio de trabajo dentro del contenedor
WORKDIR /app

# Copiamos los archivos del proyecto
COPY . /app

# Instalamos dependencias
RUN pip install --no-cache-dir flask

# Exponemos el puerto que usará la app
EXPOSE 5000

# Comando para arrancar la app
CMD ["python", "fakenodo.py"]

# Edu-Retention Backend

Backend API independiente para la aplicación móvil Edu-Retention.

## Características

- ✅ Separado del frontend
- ✅ Multi-ambiente (dev, staging, prod)
- ✅ Seguridad CORS configurable
- ✅ PostgreSQL listo para producción
- ✅ Despliegue en Azure

## Requisitos

- Python 3.11+
- PostgreSQL 13+ (para producción)
- pip

## Desarrollo Local

### 1. Setup

```bash
# Clonar o navegar al proyecto
cd Miproyecto-backend

# Crear virtual environment
python -m venv venv

# Activar (Windows)
venv\Scripts\activate
# o (macOS/Linux)
source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt
```

### 2. Configuración del Entorno

```bash
# Crear archivo .env (copiar de .env.example)
cp .env.example .env

# Editar .env con tus valores
# Para desarrollo, usar SQLite es suficiente
DATABASE_URL=sqlite:///app.db
FLASK_ENV=development
```

### 3. Ejecutar

```bash
python app.py
```

La API estará en `http://localhost:5000`

---

## Desarrollo desde Expo Go

### Usando ngrok (RECOMENDADO)

Durante desarrollo, necesitas exponer tu localhost para que Expo Go pueda acceder:

```bash
# Instalar ngrok (https://ngrok.com)
ngrok http 5000

# Copiar URL generada: https://xxxx-xx-xxx-xxx-xx.ngrok.io

# Actualizar .env
CORS_ORIGINS=http://localhost:5000,https://xxxx-xx-xxx-xxx-xx.ngrok.io

# En app.json del frontend:
```

En el frontend, actualizar `constants/api.ts`:

```typescript
// Para desarrollo local
const API_BASE_URL = __DEV__ 
  ? 'http://localhost:5000' 
  : 'https://backend-prod.azurewebsites.net';
```

---

## Despliegue en Azure (For Students)

### 1. Preparación

```bash
# Login en Azure CLI
az login

# Crear grupo de recursos
az group create \
  --name edu-retention-rg \
  --location eastus
```

### 2. Crear Base de Datos PostgreSQL

```bash
az postgres server create \
  --resource-group edu-retention-rg \
  --name edu-retention-db \
  --location eastus \
  --admin-user dbadmin \
  --admin-password YOUR-SECURE-PASSWORD \
  --sku-name B_Gen5_1 \
  --storage-size 51200
```

### 3. Crear App Service

```bash
# Crear plan
az appservice plan create \
  --name edu-retention-plan \
  --resource-group edu-retention-rg \
  --sku B1 \
  --is-linux

# Crear web app
az webapp create \
  --resource-group edu-retention-rg \
  --plan edu-retention-plan \
  --name edu-retention-backend \
  --runtime "PYTHON|3.11"
```

### 4. Configurar Variables de Entorno

```bash
az webapp config appsettings set \
  --resource-group edu-retention-rg \
  --name edu-retention-backend \
  --settings \
    DATABASE_URL="postgresql://dbadmin:PASSWORD@edu-retention-db.postgres.database.azure.com:5432/miproyecto" \
    FLASK_ENV="production" \
    SECRET_KEY="your-secure-random-key" \
    CORS_ORIGINS="https://tuapp.com,https://www.tuapp.com" \
    GUNICORN_CMD_ARGS="--workers=4 --worker-class=sync"
```

### 5. Desplegar

```bash
# Desplegar usando Git
az webapp deployment source config-zip \
  --resource-group edu-retention-rg \
  --name edu-retention-backend \
  --src-path path/to/your/app.zip
```

---

## API Endpoints (Ejemplo)

```
GET    /health                    - Health check
POST   /api/auth/login            - Login
POST   /api/auth/register         - Registro
GET    /api/users/:id             - Obtener usuario
POST   /api/surveys               - Crear encuesta
GET    /api/surveys/:id           - Obtener encuesta
```

---

## Testing

```bash
# Instalar pytest
pip install pytest

# Ejecutar tests
pytest
```

---

## Notas Importantes (Críticas para Expo Go)

1. **CORS**: Muy importante para que Expo Go pueda comunicarse
2. **HOST**: Usa `0.0.0.0` en producción, no `127.0.0.1`
3. **HTTPS**: En producción, siempre usa HTTPS
4. **Secrets**: Nunca commitear `.env` con valores reales
5. **ngrok**: Para desarrollo local con dispositivos físicos

---

## Troubleshooting

### "Connection refused" desde Expo Go

- Verificar que backend esté corriendo en 0.0.0.0:5000
- Usar ngrok si estás en dispositivo físico
- Verificar CORS_ORIGINS incluya tu IP/dominio

### "CORS error"

- Revisar CORS_ORIGINS en .env
- Asegurar que el origen exact del que viene la request esté en la lista

### Base de datos "database locked"

- Usar PostgreSQL en lugar de SQLite para producción
- SQLite tiene limitaciones de concurrencia

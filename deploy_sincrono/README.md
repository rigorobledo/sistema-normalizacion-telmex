# ⚡ Sistema Síncrono - Telmex

Sistema de procesamiento inmediato

## 🚀 Deploy en Railway

Este proyecto está configurado específicamente para **Sistema Síncrono**.

### Variables de Entorno Requeridas:
- `DATABASE_URL`: URL completa de PostgreSQL
- `PORT`: Puerto (Railway lo asigna automáticamente)

### Comando de Deploy:
```bash
git add .
git commit -m "Deploy Sistema Síncrono"
git push
```

### Características:
- ⚡ **Tipo:** Sistema Síncrono
- 🚂 **Optimizado para Railway**
- 🔒 **Sistema de autenticación integrado**
- 📊 **PostgreSQL como base de datos**

### Estructura del Proyecto:
```
sincrono/
├── app.py                              ← Punto de entrada
├── sistema_completo_normalizacion.py   ← Sistema principal
├── requirements.txt                    ← Dependencias
├── railway.json                        ← Configuración Railway
└── README.md                          ← Este archivo
```

### Para Desarrollo Local:
```bash
pip install -r requirements.txt
streamlit run app.py
```

### Soporte:
- 📧 Contacta al equipo de desarrollo para soporte
- 🔧 Logs disponibles en Railway Dashboard

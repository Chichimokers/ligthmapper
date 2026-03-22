# Light Mapper - Guía para Desarrolladores Frontend

## Concepto de la App

**Light Mapper** es una aplicación web que muestra en tiempo real el estado de la energía eléctrica en diferentes puntos geográficos. Los usuarios pueden:

- ✅ Ver inmediatamente en el mapa si hay luz o no en distintas zonas
- ✅ Reportar su propio estado de luz tocando su ubicación en el mapa
- ✅ Cambiar fácilmente su reporte (tiene luz / no tiene luz)
- ✅ Ver todos los reportes de su comunidad de forma anónima

### ¿Por qué usar Light Mapper?

- **Saber antes de salir**: ¿Hay luz en el barrio X?
- **Planificar**: ¿Cargo el celular ahora o espero?
- **Ayudar a otros**: Tu reporte ayuda a tu comunidad

### Privacidad

Tu ubicación exacta **no se muestra públicamente**. Solo se comparte:
- Si tienes luz o no
- Un punto aproximado en el mapa (redondeado)

Nunca se muestra tu email, nombre o ubicación exacta.

---

## Arquitectura de la API

### URLs

```
Producción: https://tu-dominio.com
Local:      http://localhost:8000
```

### Endpoints

| Método | Endpoint | Auth | Descripción |
|--------|----------|------|-------------|
| POST | `/api/v1/users/auth/google/` | No | Login con Google |
| GET | `/api/v1/users/profile/` | JWT | Obtener perfil propio |
| PUT | `/api/v1/users/profile/` | JWT | Actualizar ubicación y estado |
| GET | `/api/v1/users/lights/` | No | Obtener todos los reportes |
| POST | `/api/v1/users/token/refresh/` | No | Renovar token JWT |

### Respuestas de Ejemplo

**GET /api/v1/users/lights/**
```json
[
  {
    "latitude": 23.1136,
    "longitude": -82.3666,
    "has_power": true,
    "last_power_update": "2026-03-22T10:00:00Z"
  },
  {
    "latitude": 23.1200,
    "longitude": -82.3700,
    "has_power": false,
    "last_power_update": "2026-03-22T09:45:00Z"
  }
]
```

**PUT /api/v1/users/profile/**
```json
// Request
{
  "latitude": 23.1136,
  "longitude": -82.3666,
  "has_power": true
}

// Response
{
  "id": 1,
  "email": "user@gmail.com",
  "latitude": 23.1136,
  "longitude": -82.3666,
  "has_power": true,
  "last_power_update": "2026-03-22T10:30:00Z"
}
```

---

## Implementación React

### 1. Crear Proyecto

```bash
npm create vite@latest light-mapper -- --template react
cd light-mapper
npm install
npm install axios react-router-dom leaflet react-leaflet @react-oauth/google
```

### 2. Estructura de Archivos

```
src/
├── App.jsx
├── main.jsx
├── App.css
├── services/
│   └── api.js
├── hooks/
│   └── useAuth.jsx
├── components/
│   ├── Header.jsx
│   ├── Map.jsx
│   ├── PowerToggle.jsx
│   └── LoginModal.jsx
├── pages/
│   └── MapPage.jsx
└── index.css
```

### 3. Configuración de Google OAuth

```bash
npm install @react-oauth/google
```

En Google Cloud Console:
1. Crear OAuth Client ID (tipo: Aplicación web)
2. Copiar el Client ID

### 4. Archivo de Servicio API

```jsx
// src/services/api.js
import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      const refreshToken = localStorage.getItem('refresh_token');
      if (refreshToken) {
        try {
          const response = await axios.post(
            `${API_URL}/api/v1/users/token/refresh/`,
            { refresh: refreshToken }
          );
          localStorage.setItem('access_token', response.data.access);
          error.config.headers.Authorization = `Bearer ${response.data.access}`;
          return api(error.config);
        } catch {
          localStorage.removeItem('access_token');
          localStorage.removeItem('refresh_token');
          window.location.reload();
        }
      }
    }
    return Promise.reject(error);
  }
);

export default api;
```

### 5. Hook de Autenticación

```jsx
// src/hooks/useAuth.jsx
import { useState, useEffect, createContext, useContext, useCallback } from 'react';
import api from '../services/api';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const initAuth = async () => {
      const token = localStorage.getItem('access_token');
      if (token) {
        try {
          const response = await api.get('/api/v1/users/profile/');
          setUser(response.data);
        } catch {
          localStorage.removeItem('access_token');
          localStorage.removeItem('refresh_token');
        }
      }
      setLoading(false);
    };
    initAuth();
  }, []);

  const loginWithGoogle = useCallback(async (credential) => {
    try {
      const response = await api.post('/api/v1/users/auth/google/', {
        id_token: credential,
      });
      const { user, tokens } = response.data;
      localStorage.setItem('access_token', tokens.access);
      localStorage.setItem('refresh_token', tokens.refresh);
      setUser(user);
      return { success: true, user };
    } catch (error) {
      return { success: false, error: error.response?.data };
    }
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    setUser(null);
  }, []);

  const updateProfile = useCallback(async (data) => {
    try {
      const response = await api.put('/api/v1/users/profile/', data);
      setUser(response.data);
      return { success: true };
    } catch (error) {
      return { success: false, error: error.response?.data };
    }
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading, loginWithGoogle, logout, updateProfile }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
```

### 6. Componente Principal de Mapa

```jsx
// src/pages/MapPage.jsx
import { useState, useEffect, useCallback } from 'react';
import { MapContainer, TileLayer, CircleMarker, Popup } from 'react-leaflet';
import { useAuth } from '../hooks/useAuth';
import { GoogleOAuthProvider, GoogleLogin } from '@react-oauth/google';
import api from '../services/api';
import 'leaflet/dist/leaflet.css';
import './MapPage.css';

const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID;

const MapPage = () => {
  const { user, loginWithGoogle, logout, updateProfile } = useAuth();
  const [lights, setLights] = useState([]);
  const [showLoginModal, setShowLoginModal] = useState(false);
  const [isSettingLocation, setIsSettingLocation] = useState(false);
  const [mapCenter, setMapCenter] = useState(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState(null);

  useEffect(() => {
    loadLights();
    getUserLocation();
  }, []);

  useEffect(() => {
    if (user?.latitude && user?.longitude && !mapCenter) {
      setMapCenter([user.latitude, user.longitude]);
    }
  }, [user]);

  const loadLights = async () => {
    try {
      const response = await api.get('/api/v1/users/lights/');
      setLights(response.data);
    } catch (error) {
      console.error('Error cargando luces:', error);
    }
  };

  const getUserLocation = () => {
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (position) => {
          if (!mapCenter) {
            setMapCenter([
              position.coords.latitude,
              position.coords.longitude
            ]);
          }
        },
        () => {
          if (!mapCenter) {
            setMapCenter([23.1136, -82.3666]);
          }
        }
      );
    } else if (!mapCenter) {
      setMapCenter([23.1136, -82.3666]);
    }
  };

  const handleMapClick = useCallback(async (e) => {
    if (!user || !isSettingLocation) return;
    
    setLoading(true);
    const result = await updateProfile({
      latitude: parseFloat(e.latlng.lat.toFixed(7)),
      longitude: parseFloat(e.latlng.lng.toFixed(7)),
      has_power: user.has_power ?? false,
    });
    
    if (result.success) {
      setMessage('Ubicación guardada');
      setIsSettingLocation(false);
      loadLights();
    }
    setLoading(false);
  }, [user, isSettingLocation, updateProfile]);

  const togglePower = async () => {
    if (!user) {
      setShowLoginModal(true);
      return;
    }
    
    if (!user.latitude || !user.longitude) {
      setMessage('Primero selecciona tu ubicación en el mapa');
      setIsSettingLocation(true);
      return;
    }
    
    setLoading(true);
    const result = await updateProfile({
      has_power: !user.has_power,
    });
    
    if (result.success) {
      setMessage(result.user.has_power ? '💡 Reportado: Tienes luz' : '🔌 Reportado: Sin luz');
      loadLights();
    }
    setLoading(false);
    setTimeout(() => setMessage(null), 3000);
  };

  const handleGoogleSuccess = async (response) => {
    const result = await loginWithGoogle(response.credential);
    if (result.success) {
      setShowLoginModal(false);
      setMessage('Bienvenido');
    }
  };

  const stats = {
    withPower: lights.filter(l => l.has_power).length,
    withoutPower: lights.filter(l => !l.has_power).length,
  };

  return (
    <GoogleOAuthProvider clientId={GOOGLE_CLIENT_ID}>
      <div className="map-page">
        <header className="header">
          <h1>💡 Light Mapper</h1>
          <div className="header-actions">
            {user ? (
              <button onClick={logout} className="btn-user">
                <span className="user-name">{user.first_name || user.email}</span>
                <span className="logout-icon">↩</span>
              </button>
            ) : (
              <button onClick={() => setShowLoginModal(true)} className="btn-login">
                Iniciar Sesión
              </button>
            )}
          </div>
        </header>

        <div className="stats-bar">
          <div className="stat">
            <span className="stat-icon green">●</span>
            <span className="stat-value">{stats.withPower}</span>
            <span className="stat-label">Con luz</span>
          </div>
          <div className="stat">
            <span className="stat-icon red">●</span>
            <span className="stat-value">{stats.withoutPower}</span>
            <span className="stat-label">Sin luz</span>
          </div>
        </div>

        {message && (
          <div className="toast-message">{message}</div>
        )}

        <div className="map-container">
          {mapCenter && (
            <MapContainer
              center={mapCenter}
              zoom={14}
              className="map"
              onClick={handleMapClick}
            >
              <TileLayer
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                attribution='© OpenStreetMap'
              />
              
              {lights.map((light, index) => (
                <CircleMarker
                  key={index}
                  center={[light.latitude, light.longitude]}
                  pathOptions={{
                    color: light.has_power ? '#22c55e' : '#ef4444',
                    fillColor: light.has_power ? '#22c55e' : '#ef4444',
                    fillOpacity: 0.7,
                  }}
                  radius={12}
                >
                  <Popup>
                    <div className="popup-content">
                      <strong>{light.has_power ? '💡 Con Luz' : '🔌 Sin Luz'}</strong>
                      <small>Hace {formatTimeAgo(light.last_power_update)}</small>
                    </div>
                  </Popup>
                </CircleMarker>
              ))}

              {user?.latitude && user?.longitude && (
                <CircleMarker
                  center={[user.latitude, user.longitude]}
                  pathOptions={{
                    color: '#3b82f6',
                    fillColor: '#3b82f6',
                    fillOpacity: 0.9,
                  }}
                  radius={15}
                >
                  <Popup>
                    <div className="popup-content">
                      <strong>📍 Tu ubicación</strong>
                      <br />
                      <span>{user.has_power ? '💡 Tienes luz' : '🔌 Sin luz'}</span>
                    </div>
                  </Popup>
                </CircleMarker>
              )}
            </MapContainer>
          )}
        </div>

        {user && isSettingLocation && (
          <div className="instructions-overlay">
            <div className="instructions-card">
              <h3>📍 Selecciona tu ubicación</h3>
              <p>Toca en el mapa donde está tu casa</p>
              <button onClick={() => setIsSettingLocation(false)} className="btn-cancel">
                Cancelar
              </button>
            </div>
          </div>
        )}

        <div className="bottom-panel">
          {user?.latitude && user?.longitude ? (
            <div className="power-status-card">
              <div className="power-info">
                <span className="power-icon">
                  {user.has_power ? '💡' : '🔌'}
                </span>
                <span className="power-text">
                  {user.has_power ? 'Tienes luz' : 'Sin luz'}
                </span>
              </div>
              <button
                onClick={togglePower}
                className={`btn-power ${user.has_power ? 'off' : 'on'}`}
                disabled={loading}
              >
                {loading ? '...' : user.has_power ? 'Apagar' : 'Encender'}
              </button>
            </div>
          ) : (
            <div className="setup-card">
              <p>📍 Configura tu ubicación para reportar</p>
              <button
                onClick={() => setIsSettingLocation(true)}
                className="btn-setup"
              >
                Seleccionar en mapa
              </button>
            </div>
          )}
        </div>

        {showLoginModal && (
          <div className="modal-overlay" onClick={() => setShowLoginModal(false)}>
            <div className="modal-content" onClick={e => e.stopPropagation()}>
              <button className="modal-close" onClick={() => setShowLoginModal(false)}>
                ✕
              </button>
              <h2>Iniciar Sesión</h2>
              <p>Necesitas iniciar sesión para reportar tu estado de luz</p>
              <GoogleLogin
                onSuccess={handleGoogleSuccess}
                onError={() => setMessage('Error al iniciar sesión')}
                useOneTap
                theme="filled_blue"
                size="large"
                shape="rectangular"
              />
              <div className="privacy-note">
                <small>🔒 Solo usamos tu email para crear tu cuenta. Nunca compartimos tu información.</small>
              </div>
            </div>
          </div>
        )}
      </div>
    </GoogleOAuthProvider>
  );
};

const formatTimeAgo = (dateString) => {
  const date = new Date(dateString);
  const now = new Date();
  const minutes = Math.floor((now - date) / 60000);
  
  if (minutes < 1) return 'ahora';
  if (minutes < 60) return `${minutes} min`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours} h`;
  return `${Math.floor(hours / 24)} días`;
};

export default MapPage;
```

### 7. Estilos CSS (Mobile First)

```css
/* src/index.css */
:root {
  --primary: #3b82f6;
  --success: #22c55e;
  --danger: #ef4444;
  --dark: #1f2937;
  --gray: #6b7280;
  --light: #f3f4f6;
  --white: #ffffff;
}

* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

html, body, #root {
  height: 100%;
  width: 100%;
  overflow: hidden;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  background: var(--light);
  color: var(--dark);
}

/* MapPage.css */
.map-page {
  height: 100%;
  display: flex;
  flex-direction: column;
  position: relative;
}

.header {
  background: var(--white);
  padding: 12px 16px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  z-index: 1000;
}

.header h1 {
  font-size: 1.25rem;
  color: var(--primary);
}

.btn-login {
  background: var(--primary);
  color: white;
  border: none;
  padding: 8px 16px;
  border-radius: 20px;
  font-weight: 600;
  cursor: pointer;
}

.btn-user {
  display: flex;
  align-items: center;
  gap: 8px;
  background: var(--light);
  border: none;
  padding: 8px 16px;
  border-radius: 20px;
  cursor: pointer;
}

.user-name {
  max-width: 120px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.logout-icon {
  color: var(--gray);
}

/* Stats Bar */
.stats-bar {
  background: var(--white);
  display: flex;
  justify-content: space-around;
  padding: 12px;
  border-bottom: 1px solid var(--light);
}

.stat {
  display: flex;
  align-items: center;
  gap: 6px;
}

.stat-icon {
  font-size: 12px;
}

.stat-icon.green { color: var(--success); }
.stat-icon.red { color: var(--danger); }

.stat-value {
  font-weight: 700;
  font-size: 1.1rem;
}

.stat-label {
  font-size: 0.85rem;
  color: var(--gray);
}

/* Toast Message */
.toast-message {
  position: fixed;
  top: 70px;
  left: 50%;
  transform: translateX(-50%);
  background: var(--dark);
  color: white;
  padding: 12px 24px;
  border-radius: 25px;
  font-size: 0.9rem;
  z-index: 1001;
  animation: fadeInOut 3s ease;
}

@keyframes fadeInOut {
  0%, 100% { opacity: 0; transform: translateX(-50%) translateY(-10px); }
  10%, 90% { opacity: 1; transform: translateX(-50%) translateY(0); }
}

/* Map */
.map-container {
  flex: 1;
  position: relative;
}

.map {
  height: 100%;
  width: 100%;
}

.leaflet-container {
  height: 100%;
  width: 100%;
}

/* Popup */
.popup-content {
  text-align: center;
}

.popup-content strong {
  display: block;
  font-size: 1rem;
  margin-bottom: 4px;
}

.popup-content small {
  color: var(--gray);
  font-size: 0.8rem;
}

/* Instructions Overlay */
.instructions-overlay {
  position: fixed;
  bottom: 120px;
  left: 16px;
  right: 16px;
  z-index: 1000;
}

.instructions-card {
  background: var(--dark);
  color: white;
  padding: 16px;
  border-radius: 12px;
  text-align: center;
}

.instructions-card h3 {
  margin-bottom: 8px;
}

.instructions-card p {
  font-size: 0.9rem;
  opacity: 0.9;
  margin-bottom: 12px;
}

.btn-cancel {
  background: transparent;
  border: 1px solid white;
  color: white;
  padding: 8px 24px;
  border-radius: 20px;
  cursor: pointer;
}

/* Bottom Panel */
.bottom-panel {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  padding: 16px;
  z-index: 1000;
}

.power-status-card {
  background: var(--white);
  border-radius: 16px;
  padding: 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  box-shadow: 0 -4px 20px rgba(0,0,0,0.15);
}

.power-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.power-icon {
  font-size: 2rem;
}

.power-text {
  font-size: 1.1rem;
  font-weight: 600;
}

.btn-power {
  padding: 14px 32px;
  border: none;
  border-radius: 25px;
  font-size: 1rem;
  font-weight: 700;
  cursor: pointer;
  transition: transform 0.2s;
}

.btn-power:active {
  transform: scale(0.95);
}

.btn-power.on {
  background: var(--success);
  color: white;
}

.btn-power.off {
  background: var(--danger);
  color: white;
}

.setup-card {
  background: var(--white);
  border-radius: 16px;
  padding: 20px;
  text-align: center;
  box-shadow: 0 -4px 20px rgba(0,0,0,0.15);
}

.setup-card p {
  margin-bottom: 12px;
  color: var(--gray);
}

.btn-setup {
  background: var(--primary);
  color: white;
  border: none;
  padding: 14px 32px;
  border-radius: 25px;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
}

/* Modal */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0,0,0,0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2000;
  padding: 16px;
}

.modal-content {
  background: var(--white);
  border-radius: 20px;
  padding: 32px 24px;
  width: 100%;
  max-width: 400px;
  text-align: center;
  position: relative;
}

.modal-close {
  position: absolute;
  top: 12px;
  right: 16px;
  background: none;
  border: none;
  font-size: 1.5rem;
  cursor: pointer;
  color: var(--gray);
}

.modal-content h2 {
  margin-bottom: 8px;
}

.modal-content p {
  color: var(--gray);
  margin-bottom: 24px;
}

.privacy-note {
  margin-top: 20px;
  padding: 12px;
  background: var(--light);
  border-radius: 8px;
}

.privacy-note small {
  color: var(--gray);
}

/* Desktop Adjustments */
@media (min-width: 768px) {
  .bottom-panel {
    left: 50%;
    right: auto;
    transform: translateX(-50%);
    width: 400px;
  }
  
  .instructions-overlay {
    left: 50%;
    right: auto;
    transform: translateX(-50%);
    width: 400px;
  }
}
```

### 8. App.jsx

```jsx
// src/App.jsx
import { AuthProvider } from './hooks/useAuth';
import MapPage from './pages/MapPage';
import './App.css';

function App() {
  return (
    <AuthProvider>
      <MapPage />
    </AuthProvider>
  );
}

export default App;
```

### 9. Variables de Entorno

```bash
# .env
VITE_API_URL=https://tu-dominio.com
VITE_GOOGLE_CLIENT_ID=tu-client-id.apps.googleusercontent.com
```

---

## Flujo de Usuario

```
1. Usuario abre la app
   ↓
2. Ve el mapa inmediatamente centrado en su ubicación GPS
   ↓
3. Ve puntos verdes (con luz) y rojos (sin luz) en el mapa
   ↓
4. Quiere reportar → Toca "Iniciar Sesión"
   ↓
5. Se loguea con Google
   ↓
6. Toca "Seleccionar en mapa" 
   ↓
7. Toca en el mapa donde está su casa
   ↓
8. Toca el botón "Encender" o "Apagar"
   ↓
9. Su punto aparece en el mapa
   ↓
10. Puede cambiar su estado en cualquier momento tocando el botón
```

---

## Dependencias

```bash
npm install axios react-router-dom leaflet react-leaflet @react-oauth/google
```

---

## Configuración del Backend

 Asegúrate de que en `.env` del backend:

```env
GOOGLE_CLIENT_ID=tu-client-id.apps.googleusercontent.com
DEBUG=False
ALLOWED_HOSTS=tu-dominio.com
```

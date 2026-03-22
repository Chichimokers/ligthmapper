# Light Mapper - Guía para Desarrolladores Frontend

## ¿Qué es Light Mapper?

**Light Mapper** es una aplicación que permite a los usuarios reportar y consultar el estado del servicio eléctrico en diferentes ubicaciones geográficas.

### Problema que resuelve

En muchas zonas, los cortes de luz son frecuentes y recurrentes. La gente necesita saber:
- ¿Hay luz en la zona X?
- ¿Cuánto tiempo llevan sin luz?
- ¿Volvió la luz en mi barrio?

### ¿Por qué deberías aportar tus datos?

Al reportar tu estado de luz, ayudas a toda tu comunidad:
- **Información en tiempo real**: Otros saben si hay luz cerca de donde necesitan ir
- **Toma de decisiones**: Saber si cargar el celular, usar el bombón, o hacer la compra
- **Solidaridad comunitaria**: Ayudas a otros a planificar su día

Tus datos son **anónimos** - solo se comparte tu ubicación y estado de luz, nunca tu identidad.

---

## Arquitectura de la API

### URL Base
```
Producción: https://tu-dominio.com
Desarrollo: http://localhost:8000
```

### Endpoints

| Método | Endpoint | Auth | Descripción |
|--------|----------|------|-------------|
| POST | `/api/v1/users/auth/google/` | No | Login con Google |
| GET | `/api/v1/users/profile/` | JWT | Ver perfil propio |
| PUT | `/api/v1/users/profile/` | JWT | Actualizar perfil y ubicación |
| GET | `/api/v1/users/lights/` | No | Ver todos los reportes de luz |
| GET | `/api/v1/users/admin/lights/` | Admin | Ver reportes con datos de usuario |

---

## Implementación en React (Web + Móvil)

### 1. Configuración Inicial

```bash
npx create-react-app light-mapper
# o
npm create vite@latest light-mapper -- --template react
cd light-mapper
npm install axios @react-google-login/gapi googleapis
```

### 2. Configuración de Google OAuth

#### Google Cloud Console
1. Ve a https://console.cloud.google.com/apis/credentials
2. Crea un OAuth Client ID (tipo: Aplicación web)
3. Copia el **Client ID**

#### En tu React App

```bash
npm install @react-oauth/google jwt-decode
```

```jsx
// src/components/GoogleLoginButton.jsx
import { GoogleLogin } from '@react-oauth/google';

const GoogleLoginButton = ({ onSuccess, onError }) => {
  return (
    <GoogleLogin
      client_id="TU_GOOGLE_CLIENT_ID.apps.googleusercontent.com"
      onSuccess={onSuccess}
      onError={onError}
      useOneTap
      theme="outline"
      size="large"
      text="signin_with"
      shape="rectangular"
    />
  );
};

export default GoogleLoginButton;
```

### 3. Servicio de API

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
          const response = await axios.post(`${API_URL}/api/v1/users/token/refresh/`, {
            refresh: refreshToken,
          });
          localStorage.setItem('access_token', response.data.access);
          error.config.headers.Authorization = `Bearer ${response.data.access}`;
          return api(error.config);
        } catch (refreshError) {
          localStorage.removeItem('access_token');
          localStorage.removeItem('refresh_token');
          window.location.href = '/login';
        }
      }
    }
    return Promise.reject(error);
  }
);

export default api;
```

### 4. hooks/useAuth.js

```jsx
// src/hooks/useAuth.js
import { useState, useEffect, createContext, useContext } from 'react';
import api from '../services/api';
import jwt_decode from 'jwt-decode';

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
        } catch (error) {
          console.log('Token inválido, esperando login...');
        }
      }
      setLoading(false);
    };
    initAuth();
  }, []);

  const loginWithGoogle = async (credential) => {
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
  };

  const logout = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    setUser(null);
  };

  const updateProfile = async (data) => {
    try {
      const response = await api.put('/api/v1/users/profile/', data);
      setUser(response.data);
      return { success: true };
    } catch (error) {
      return { success: false, error: error.response?.data };
    }
  };

  return (
    <AuthContext.Provider value={{ user, loading, loginWithGoogle, logout, updateProfile }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
```

### 5. Componentes de la Aplicación

#### App.jsx (Layout Principal)

```jsx
// src/App.jsx
import { AuthProvider } from './hooks/useAuth';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import LoginPage from './pages/LoginPage';
import HomePage from './pages/HomePage';
import ProfilePage from './pages/ProfilePage';
import MapPage from './pages/MapPage';
import './App.css';

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <div className="app">
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/profile" element={<ProfilePage />} />
            <Route path="/map" element={<MapPage />} />
          </Routes>
        </div>
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;
```

#### LoginPage.jsx

```jsx
// src/pages/LoginPage.jsx
import { GoogleLogin } from '@react-oauth/google';
import { useAuth } from '../hooks/useAuth';
import { useNavigate } from 'react-router-dom';
import './LoginPage.css';

const LoginPage = () => {
  const { loginWithGoogle } = useAuth();
  const navigate = useNavigate();

  const handleGoogleSuccess = async (response) => {
    const result = await loginWithGoogle(response.credential);
    if (result.success) {
      navigate('/');
    }
  };

  const handleGoogleError = () => {
    console.log('Login Fallido');
  };

  return (
    <div className="login-container">
      <div className="login-card">
        <h1>Light Mapper</h1>
        <p>Reporta y consulta el estado de luz en tu zona</p>
        
        <GoogleLogin
          client_id="TU_CLIENT_ID.apps.googleusercontent.com"
          onSuccess={handleGoogleSuccess}
          onError={handleGoogleError}
          useOneTap
          theme="filled_blue"
          size="large"
          shape="pill"
        />
        
        <div className="info-section">
          <h3>¿Por qué aportar tus datos?</h3>
          <ul>
            <li>Ayudas a tu comunidad</li>
            <li>Información en tiempo real</li>
            <li>Sin comprometer tu privacidad</li>
          </ul>
        </div>
      </div>
    </div>
  );
};

export default LoginPage;
```

#### HomePage.jsx (Dashboard Principal)

```jsx
// src/pages/HomePage.jsx
import { useState, useEffect } from 'react';
import api from '../services/api';
import { useAuth } from '../hooks/useAuth';
import { Link } from 'react-router-dom';
import './HomePage.css';

const HomePage = () => {
  const { user } = useAuth();
  const [lights, setLights] = useState([]);
  const [stats, setStats] = useState({ withPower: 0, withoutPower: 0, total: 0 });

  useEffect(() => {
    loadLights();
  }, []);

  const loadLights = async () => {
    try {
      const response = await api.get('/api/v1/users/lights/');
      setLights(response.data);
      
      const withPower = response.data.filter(l => l.has_power).length;
      setStats({
        withPower,
        withoutPower: response.data.length - withPower,
        total: response.data.length,
      });
    } catch (error) {
      console.error('Error cargando luces:', error);
    }
  };

  return (
    <div className="home-container">
      <header className="home-header">
        <h1>Light Mapper</h1>
        <nav>
          <Link to="/">Inicio</Link>
          <Link to="/map">Mapa</Link>
          <Link to="/profile">Perfil</Link>
        </nav>
      </header>

      <div className="stats-grid">
        <div className="stat-card green">
          <span className="stat-number">{stats.withPower}</span>
          <span className="stat-label">Con Luz</span>
        </div>
        <div className="stat-card red">
          <span className="stat-number">{stats.withoutPower}</span>
          <span className="stat-label">Sin Luz</span>
        </div>
        <div className="stat-card gray">
          <span className="stat-number">{stats.total}</span>
          <span className="stat-label">Total</span>
        </div>
      </div>

      {!user && (
        <div className="cta-banner">
          <h2>¿Tienes luz?</h2>
          <p>Inicia sesión para reportar tu estado y ayudar a tu comunidad</p>
          <Link to="/login" className="btn-primary">Reportar Ahora</Link>
        </div>
      )}

      {user && !user.latitude && (
        <div className="setup-banner">
          <h2>Configura tu ubicación</h2>
          <p>Para reportar tu estado de luz, primero configura tu ubicación</p>
          <Link to="/profile" className="btn-primary">Ir al Perfil</Link>
        </div>
      )}

      <div className="lights-list">
        <h2>Reportes Recientes</h2>
        {lights.slice(0, 10).map((light, index) => (
          <div key={index} className={`light-item ${light.has_power ? 'on' : 'off'}`}>
            <div className="light-status">
              {light.has_power ? '💡' : '🔌'}
            </div>
            <div className="light-info">
              <span className="status-text">
                {light.has_power ? 'Con Luz' : 'Sin Luz'}
              </span>
              <span className="light-coords">
                {light.latitude}, {light.longitude}
              </span>
              <span className="light-time">
                Actualizado: {new Date(light.last_power_update).toLocaleString()}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default HomePage;
```

#### ProfilePage.jsx (Configuración de Ubicación)

```jsx
// src/pages/ProfilePage.jsx
import { useState } from 'react';
import { useAuth } from '../hooks/useAuth';
import { useNavigate } from 'react-router-dom';
import './ProfilePage.css';

const ProfilePage = () => {
  const { user, logout, updateProfile } = useAuth();
  const navigate = useNavigate();
  
  const [formData, setFormData] = useState({
    latitude: user?.latitude || '',
    longitude: user?.longitude || '',
    has_power: user?.has_power ?? null,
  });
  
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState(null);

  const getLocation = () => {
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (position) => {
          setFormData(prev => ({
            ...prev,
            latitude: position.coords.latitude.toFixed(7),
            longitude: position.coords.longitude.toFixed(7),
          }));
        },
        (error) => {
          console.error('Error de geolocalización:', error);
          setMessage('No se pudo obtener tu ubicación');
        }
      );
    } else {
      setMessage('Tu navegador no soporta geolocalización');
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    
    const result = await updateProfile({
      latitude: parseFloat(formData.latitude),
      longitude: parseFloat(formData.longitude),
      has_power: formData.has_power,
    });
    
    if (result.success) {
      setMessage('¡Perfil actualizado!');
      setTimeout(() => navigate('/'), 1500);
    } else {
      setMessage('Error al actualizar');
    }
    
    setLoading(false);
  };

  return (
    <div className="profile-container">
      <header className="profile-header">
        <h1>Mi Perfil</h1>
        <button onClick={logout} className="btn-logout">Cerrar Sesión</button>
      </header>

      <form onSubmit={handleSubmit} className="profile-form">
        <div className="user-info">
          <img 
            src={`https://ui-avatars.com/api/?name=${user?.first_name || user?.email}`} 
            alt="Avatar"
          />
          <div>
            <h2>{user?.first_name} {user?.last_name}</h2>
            <p>{user?.email}</p>
          </div>
        </div>

        <div className="form-section">
          <h3>📍 Mi Ubicación</h3>
          <p className="section-desc">
            Tu ubicación se usa para mostrar tu estado de luz en el mapa
          </p>
          
          <div className="location-inputs">
            <div className="input-group">
              <label>Latitud</label>
              <input
                type="text"
                value={formData.latitude}
                onChange={(e) => setFormData(prev => ({...prev, latitude: e.target.value}))}
                placeholder="23.1136000"
              />
            </div>
            <div className="input-group">
              <label>Longitud</label>
              <input
                type="text"
                value={formData.longitude}
                onChange={(e) => setFormData(prev => ({...prev, longitude: e.target.value}))}
                placeholder="-82.3666000"
              />
            </div>
          </div>
          
          <button type="button" onClick={getLocation} className="btn-gps">
            📍 Usar mi ubicación actual
          </button>
        </div>

        <div className="form-section">
          <h3>⚡ Estado de Luz</h3>
          <p className="section-desc">
            ¿Tienes luz actualmente en tu ubicación?
          </p>
          
          <div className="power-options">
            <button
              type="button"
              className={`power-btn ${formData.has_power === true ? 'active' : ''}`}
              onClick={() => setFormData(prev => ({...prev, has_power: true}))}
            >
              💡 Tengo Luz
            </button>
            <button
              type="button"
              className={`power-btn off ${formData.has_power === false ? 'active' : ''}`}
              onClick={() => setFormData(prev => ({...prev, has_power: false}))}
            >
              🔌 Sin Luz
            </button>
          </div>
        </div>

        {message && <div className="message">{message}</div>}

        <button type="submit" className="btn-submit" disabled={loading}>
          {loading ? 'Guardando...' : 'Guardar Cambios'}
        </button>
      </form>
    </div>
  );
};

export default ProfilePage;
```

#### MapPage.jsx (Visualización en Mapa)

```jsx
// src/pages/MapPage.jsx
import { useState, useEffect } from 'react';
import api from '../services/api';
import { MapContainer, TileLayer, CircleMarker, Popup } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import './MapPage.css';

const MapPage = () => {
  const [lights, setLights] = useState([]);

  useEffect(() => {
    loadLights();
  }, []);

  const loadLights = async () => {
    try {
      const response = await api.get('/api/v1/users/lights/');
      setLights(response.data);
    } catch (error) {
      console.error('Error cargando luces:', error);
    }
  };

  const center = lights.length > 0 
    ? [lights[0].latitude, lights[0].longitude] 
    : [23.1136, -82.3666]; // Cuba por defecto

  return (
    <div className="map-container">
      <header className="map-header">
        <h1>Mapa de Luz</h1>
        <div className="legend">
          <span className="legend-item green">● Con Luz</span>
          <span className="legend-item red">● Sin Luz</span>
        </div>
      </header>
      
      <MapContainer center={center} zoom={10} className="map">
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
            radius={10}
          >
            <Popup>
              <div className="map-popup">
                <strong>{light.has_power ? '💡 Con Luz' : '🔌 Sin Luz'}</strong>
                <br />
                <small>
                  Actualizado: {new Date(light.last_power_update).toLocaleString()}
                </small>
              </div>
            </Popup>
          </CircleMarker>
        ))}
      </MapContainer>
    </div>
  );
};

export default MapPage;
```

### 6. Estilos CSS (App.css - Mobile First)

```css
/* src/App.css */
:root {
  --primary: #3b82f6;
  --primary-dark: #2563eb;
  --success: #22c55e;
  --danger: #ef4444;
  --gray-100: #f3f4f6;
  --gray-200: #e5e7eb;
  --gray-500: #6b7280;
  --gray-800: #1f2937;
}

* {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  background: var(--gray-100);
  color: var(--gray-800);
  line-height: 1.5;
}

.app {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

/* Mobile First - todas las pantallas menores a 768px */
.container {
  padding: 1rem;
  max-width: 100%;
}

/* Tablet */
@media (min-width: 768px) {
  .container {
    max-width: 720px;
    margin: 0 auto;
    padding: 2rem;
  }
}

/* Desktop */
@media (min-width: 1024px) {
  .container {
    max-width: 960px;
  }
}

/* Header */
header {
  background: white;
  padding: 1rem;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
  position: sticky;
  top: 0;
  z-index: 100;
}

header h1 {
  font-size: 1.25rem;
  color: var(--primary);
}

nav {
  display: flex;
  gap: 1rem;
  margin-top: 0.5rem;
}

nav a {
  color: var(--gray-500);
  text-decoration: none;
  font-size: 0.875rem;
}

nav a:hover {
  color: var(--primary);
}

/* Cards */
.card {
  background: white;
  border-radius: 0.75rem;
  padding: 1.5rem;
  margin: 1rem 0;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}

/* Buttons */
.btn-primary {
  background: var(--primary);
  color: white;
  padding: 0.75rem 1.5rem;
  border: none;
  border-radius: 0.5rem;
  font-weight: 600;
  cursor: pointer;
  text-decoration: none;
  display: inline-block;
}

.btn-primary:hover {
  background: var(--primary-dark);
}

/* Stats Grid */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 0.75rem;
  margin: 1rem 0;
}

.stat-card {
  background: white;
  padding: 1rem;
  border-radius: 0.75rem;
  text-align: center;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}

.stat-card.green { border-left: 4px solid var(--success); }
.stat-card.red { border-left: 4px solid var(--danger); }
.stat-card.gray { border-left: 4px solid var(--gray-500); }

.stat-number {
  display: block;
  font-size: 2rem;
  font-weight: 700;
}

.stat-label {
  font-size: 0.75rem;
  color: var(--gray-500);
}

/* Light Items */
.light-item {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1rem;
  background: white;
  border-radius: 0.5rem;
  margin: 0.5rem 0;
}

.light-item.on { border-left: 4px solid var(--success); }
.light-item.off { border-left: 4px solid var(--danger); }

.light-status {
  font-size: 1.5rem;
}

.light-info {
  flex: 1;
}

.status-text {
  font-weight: 600;
  display: block;
}

.light-coords, .light-time {
  font-size: 0.75rem;
  color: var(--gray-500);
}

/* Login Page */
.login-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1rem;
  background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
}

.login-card {
  background: white;
  padding: 2rem;
  border-radius: 1rem;
  text-align: center;
  max-width: 400px;
  width: 100%;
}

.login-card h1 {
  color: var(--primary);
  margin-bottom: 0.5rem;
}

.login-card p {
  color: var(--gray-500);
  margin-bottom: 2rem;
}

.info-section {
  margin-top: 2rem;
  text-align: left;
  padding-top: 1rem;
  border-top: 1px solid var(--gray-200);
}

.info-section h3 {
  font-size: 0.875rem;
  margin-bottom: 0.5rem;
}

.info-section ul {
  list-style: none;
  font-size: 0.875rem;
  color: var(--gray-500);
}

.info-section li::before {
  content: '✓ ';
  color: var(--success);
}

/* Profile Form */
.profile-form {
  padding: 1rem;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-bottom: 2rem;
}

.user-info img {
  width: 60px;
  height: 60px;
  border-radius: 50%;
}

.form-section {
  background: white;
  padding: 1.5rem;
  border-radius: 0.75rem;
  margin-bottom: 1rem;
}

.form-section h3 {
  margin-bottom: 0.5rem;
}

.section-desc {
  font-size: 0.875rem;
  color: var(--gray-500);
  margin-bottom: 1rem;
}

.input-group {
  margin-bottom: 1rem;
}

.input-group label {
  display: block;
  font-size: 0.875rem;
  font-weight: 500;
  margin-bottom: 0.25rem;
}

.input-group input {
  width: 100%;
  padding: 0.75rem;
  border: 1px solid var(--gray-200);
  border-radius: 0.5rem;
  font-size: 1rem;
}

.power-options {
  display: flex;
  gap: 0.5rem;
}

.power-btn {
  flex: 1;
  padding: 1rem;
  border: 2px solid var(--gray-200);
  border-radius: 0.5rem;
  background: white;
  cursor: pointer;
  font-weight: 500;
}

.power-btn.active {
  border-color: var(--success);
  background: rgba(34, 197, 94, 0.1);
}

.power-btn.off.active {
  border-color: var(--danger);
  background: rgba(239, 68, 68, 0.1);
}

/* Map */
.map-container {
  height: calc(100vh - 60px);
  position: relative;
}

.map-header {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  background: white;
  padding: 0.75rem 1rem;
  z-index: 1000;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.map {
  height: 100%;
  width: 100%;
}

.legend {
  display: flex;
  gap: 1rem;
  font-size: 0.75rem;
}

.legend-item.green { color: var(--success); }
.legend-item.red { color: var(--danger); }
```

### 7. Instalación de Dependencias Adicionales

```bash
npm install react-router-dom axios leaflet react-leaflet @react-oauth/google
```

---

## Variables de Entorno

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
2. Ve pantalla de login con Google (o ve mapa directamente si es público)
   ↓
3. Inicia sesión con Google
   ↓
4. Se le pide configurar ubicación (si no la tiene)
   ↓
5. Reporta si tiene luz o no
   ↓
6. Puede ver el mapa con todos los reportes
   ↓
7. Puede actualizar su estado en cualquier momento
```

---

## Preguntas Frecuentes

### ¿Mis datos son privados?
Solo se comparte tu latitud, longitud y estado de luz. Tu email y nombre NO se muestran publicly.

### ¿Necesito cuenta para ver el mapa?
No. El mapa de luces es público y no requiere autenticación.

### ¿Cada vez que cambio mi estado tengo que reportar?
Sí. El sistema no automatiza nada. Tu reporte es manual para mayor precisión.

### ¿Puedo ver quién reporta qué?
Solo los administradores pueden ver los datos completos de cada usuario.

---

## Soporte

Para problemas o sugerencias, contactar al equipo de desarrollo.

document.getElementById('loginForm').addEventListener('submit', function(e) {
  e.preventDefault();

  const usuario = document.getElementById('usuario').value.trim();
  const contrasena = document.getElementById('contrasena').value.trim();
  const errorMsg = document.getElementById('error_msg');
  const btn = document.querySelector('.btn-login');

  errorMsg.textContent = '';
  btn.textContent = 'Ingresando...';
  btn.disabled = true;

  fetch('https://inteligencia.onrender.com/api/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ usuario: usuario, contrasena: contrasena })
  })
  .then(res => res.json())
  .then(data => {
    if (data.exito) {
      sessionStorage.setItem('qbd_admin', data.usuario);
      sessionStorage.setItem('qbd_rol', data.rol);
      sessionStorage.setItem('qbd_nombre', data.nombre);
      window.location.href = 'dashboard.html';
    } else {
      errorMsg.textContent = data.mensaje || 'Usuario o contraseña incorrectos';
      document.getElementById('contrasena').value = '';
      btn.textContent = 'Iniciar Sesión';
      btn.disabled = false;
    }
  })
  .catch(() => {
    errorMsg.textContent = 'Error de conexion con el servidor';
    btn.textContent = 'Iniciar Sesion';
    btn.disabled = false;
  });
});

if (sessionStorage.getItem('qbd_admin')) {
  window.location.href = 'dashboard.html';
}

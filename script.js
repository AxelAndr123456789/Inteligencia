document.addEventListener('DOMContentLoaded', () => {

  // Mobile menu toggle
  const menuToggle = document.getElementById('menuToggle');
  const navLinks = document.getElementById('navLinks');
  menuToggle.addEventListener('click', () => {
    navLinks.classList.toggle('active');
  });

  navLinks.querySelectorAll('a').forEach(link => {
    link.addEventListener('click', () => {
      navLinks.classList.remove('active');
    });
  });

  // FAQ accordion
  document.querySelectorAll('.faq-question').forEach(btn => {
    btn.addEventListener('click', () => {
      const item = btn.parentElement;
      const isActive = item.classList.contains('active');
      document.querySelectorAll('.faq-item').forEach(i => i.classList.remove('active'));
      if (!isActive) item.classList.add('active');
    });
  });

  // Scroll animations
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) entry.target.classList.add('visible');
    });
  }, { threshold: 0.1 });

  document.querySelectorAll(
    '.stat-card, .mv-card, .value-item, .product-card, .service-card, .why-item, .contact-card, .faq-item, .timeline-item, .commitment-icons'
  ).forEach(el => {
    el.classList.add('animate-in');
    observer.observe(el);
  });

  // ===== CHATBOT CON API ML =====
  const API_URL = 'https://inteligencia.onrender.com/api/chat';
  const API_REC_URL = 'https://inteligencia.onrender.com/api/recomendar';
  const fab = document.getElementById('chatbotFab');
  const win = document.getElementById('chatbotWindow');
  const closeBtn = document.getElementById('chatbotClose');
  const msgs = document.getElementById('chatbotMessages');
  const input = document.getElementById('chatbotInput');
  const sendBtn = document.getElementById('chatbotSend');

  const robotSVG = `<img src="../img/chatbot.png" alt="QbD Bot" width="22" height="22" style="border-radius:50%;">`;
  const userSVG = `<svg viewBox="0 0 24 24" width="18" height="18" fill="#6366f1"><path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/></svg>`;

  const suggestions = [
    "¿Qué es una fórmula magistral?",
    "¿Dónde están ubicados?",
    "¿Qué servicios ofrecen?",
    "Tengo dolor de estómago"
  ];

  let isOpen = false;
  let isFirstMsg = true;

  function toggleChat() {
    isOpen = !isOpen;
    win.classList.toggle('open', isOpen);
    if (isOpen && msgs.children.length === 0) {
      isFirstMsg = true;
      addBotMsg("¡Hola! Soy **QbD Bot**, tu asistente virtual de QbD Farmacia Magistral. ¿En qué puedo ayudarte hoy?");
      showSuggestions(suggestions);
    }
    if (isOpen) {
      setTimeout(() => { msgs.scrollTop = msgs.scrollHeight; }, 100);
    }
  }

  fab.addEventListener('click', toggleChat);
  closeBtn.addEventListener('click', toggleChat);

  function addBotMsg(text) {
    const div = document.createElement('div');
    div.className = 'chat-msg bot';
    div.innerHTML = `<div class="chat-avatar">${robotSVG}</div><div class="chat-bubble">${text}</div>`;
    msgs.appendChild(div);
    setTimeout(() => { msgs.scrollTop = msgs.scrollHeight; }, 50);
    isFirstMsg = false;
  }

  function addUserMsg(text) {
    const div = document.createElement('div');
    div.className = 'chat-msg user';
    div.innerHTML = `<div class="chat-avatar">${userSVG}</div><div class="chat-bubble">${text}</div>`;
    msgs.appendChild(div);
    setTimeout(() => { msgs.scrollTop = msgs.scrollHeight; }, 50);
  }

  function showSuggestions(arr) {
    const container = document.createElement('div');
    container.className = 'chat-suggestions';
    arr.forEach(text => {
      const btn = document.createElement('button');
      btn.className = 'chat-suggest-btn';
      btn.textContent = text;
      btn.addEventListener('click', () => {
        container.remove();
        handleUserInput(text);
      });
      container.appendChild(btn);
    });
    msgs.appendChild(container);
    setTimeout(() => { msgs.scrollTop = msgs.scrollHeight; }, 50);
  }

  // Enviar mensaje a la API del chatbot ML
  async function enviarAMl(mensaje) {
    try {
      const response = await fetch(API_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mensaje })
      });
      const data = await response.json();
      return data.respuesta || "No pude procesar tu consulta. Intenta de nuevo.";
    } catch (error) {
      console.error('Error al conectar con el chatbot:', error);
      return "Estoy teniendo problemas para conectarme. Asegúrate de que el servidor esté ejecutándose. (python api.py)";
    }
  }

  // Modelo ML 2: Recomendacion de productos por sintomas
  async function recomendarProducto(mensaje) {
    try {
      const response = await fetch(API_REC_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mensaje })
      });
      const data = await response.json();
      if (data.encontrado) {
        let respuesta = `Segun tus sintomas, te recomiendo:\n\n`;
        data.productos.forEach((p, i) => {
          respuesta += `${i + 1}. **${p.DescripcionPT || p.CodProducto}**\n`;
          respuesta += `   Precio: S/ ${p.CostoUnitarioPT}\n`;
          respuesta += `   Uso: ${p.DescripcionUso}\n\n`;
        });
        respuesta += ` ${data.explicacion}\n\nConfianza del modelo: ${data.confianza}%`;
        return respuesta;
      }
      return null;
    } catch (error) {
      console.error('Error en recomendacion:', error);
      return null;
    }
  }

  async function handleUserInput(text) {
    if (!text.trim()) return;
    addUserMsg(text);
    input.value = '';

    // Mostrar indicador de "escribiendo..."
    const typing = document.createElement('div');
    typing.className = 'chat-msg bot';
    typing.innerHTML = `<div class="chat-avatar">${robotSVG}</div><div class="chat-bubble" style="color:#999;">Escribiendo...</div>`;
    msgs.appendChild(typing);
    setTimeout(() => { msgs.scrollTop = msgs.scrollHeight; }, 50);

    const respuesta = await enviarMensaje(text);
    
    typing.remove();
    
    addBotMsg(respuesta);

    showSuggestions([
      "¿Hay algo más que quieras saber?",
      "¿Qué es una fórmula magistral?",
      "¿Dónde están ubicados?"
    ]);
  }

  sendBtn.addEventListener('click', () => handleUserInput(input.value));
  input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') handleUserInput(input.value);
  });

});

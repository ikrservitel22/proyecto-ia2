const btn = document.getElementById("speakBtn");
const stopBtn = document.getElementById("stopBtn");
const respuestaEl = document.getElementById("respuesta");

let currentController = null;


stopBtn.addEventListener("click", async () => {
    
    if (currentController) {
        currentController.abort();
        currentController = null;
    }

    
    try {
        await fetch("/stop");
    } catch (e) {
        
    }

    respuestaEl.textContent = "⏹️ Bot detenido.";
    btn.disabled = false;
    btn.textContent = "🎤 Hablar";
    stopBtn.disabled = true;
});


btn.addEventListener("click", async () => {
    btn.disabled = true;
    stopBtn.disabled = false;
    btn.textContent = "⏳ Escuchando...";
    respuestaEl.textContent = "Procesando...";

    currentController = new AbortController();
    const timeoutId = setTimeout(() => currentController.abort(), 20000);

    try {
        const res = await fetch("/speak", { signal: currentController.signal });
        clearTimeout(timeoutId);

        if (!res.ok) {
            throw new Error(`Error del servidor: ${res.status}`);
        }

        const data = await res.json();

        if (Array.isArray(data.respuesta)) {
            respuestaEl.textContent = data.respuesta[0];
        } else {
            respuestaEl.textContent = data.respuesta;
        }

    } catch (err) {
        clearTimeout(timeoutId);
        if (err.name === "AbortError") {
            respuestaEl.textContent = "⏹️ Bot detenido.";
        } else {
            console.error("Error:", err);
            respuestaEl.textContent = "❌ Error al conectar con el bot.";
        }
    } finally {
        currentController = null;
        btn.disabled = false;
        stopBtn.disabled = true;
        btn.textContent = "🎤 Hablar";
    }
});
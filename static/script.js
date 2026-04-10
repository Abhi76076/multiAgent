const startBtn = document.getElementById('start-btn');
const topicInput = document.getElementById('topic-input');
const feedContainer = document.getElementById('feed-container');
const sysStatus = document.querySelector('.sys-status');
const statusText = document.getElementById('connection-status');

const agentsMap = {
    'Moderator': 'card-moderator',
    'Agent Alpha': 'card-alpha',
    'Agent Beta': 'card-beta'
};

let ws = null;

function appendSystemMessage(text, isRoundMarker = false) {
    const el = document.createElement('div');
    el.className = isRoundMarker ? 'feed-message round-marker' : 'feed-message system';
    
    const content = document.createElement('div');
    content.className = 'msg-content';
    content.textContent = isRoundMarker ? text : `SYS> ${text}`;
    
    el.appendChild(content);
    feedContainer.appendChild(el);
    scrollToBottom();
}

function appendAgentMessage(agent, text) {
    const el = document.createElement('div');
    el.className = 'feed-message';
    el.setAttribute('data-agent', agent);
    
    const header = document.createElement('div');
    header.className = 'msg-header';
    header.textContent = `[${agent.toUpperCase()}]`;
    
    const contentBox = document.createElement('div');
    contentBox.className = 'msg-content';
    
    const textSpan = document.createElement('span');
    const cursor = document.createElement('span');
    cursor.className = 'typing-cursor';
    
    contentBox.appendChild(textSpan);
    contentBox.appendChild(cursor);
    
    el.appendChild(header);
    el.appendChild(contentBox);
    feedContainer.appendChild(el);
    scrollToBottom();

    // Typewriter effect
    let i = 0;
    const speed = 10; // ms per char
    
    function typeWriter() {
        if (i < text.length) {
            // grab chunks for speed
            const chunkSize = Math.max(1, Math.floor(text.length / 50)); 
            textSpan.textContent += text.substring(i, i + chunkSize);
            i += chunkSize;
            scrollToBottom();
            setTimeout(typeWriter, speed);
        } else {
            // done
            textSpan.textContent = text; // ensure full text
            cursor.remove();
        }
    }
    
    typeWriter();
}

function updateAgentStatus(agent, status) {
    const cardId = agentsMap[agent];
    if (!cardId) return;
    
    const card = document.getElementById(cardId);
    const activityInfo = document.getElementById(`activity-${cardId.split('-')[1]}`);
    
    if (status === 'thinking') {
        card.classList.add('thinking');
        activityInfo.textContent = 'COMPUTING RESPONSE...';
    } else {
        card.classList.remove('thinking');
        activityInfo.textContent = 'IDLE';
    }
}

function scrollToBottom() {
    feedContainer.scrollTop = feedContainer.scrollHeight;
}

startBtn.addEventListener('click', () => {
    // Clear feed
    feedContainer.innerHTML = '';
    appendSystemMessage('Initializing neural link to Gemini Models...');
    
    startBtn.disabled = true;
    startBtn.querySelector('span').textContent = 'SIMULATION RUNNING';
    topicInput.disabled = true;

    // Connect to WS
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    ws = new WebSocket(`${protocol}//${window.location.host}/ws/simulate`);
    
    ws.onopen = () => {
        sysStatus.classList.add('active');
        statusText.textContent = 'LINK ACTIVE';
        appendSystemMessage('Neural link established. Transmitting parameters.');
        
        ws.send(JSON.stringify({ topic: topicInput.value }));
    };
    
    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        
        switch(data.type) {
            case 'status':
                updateAgentStatus(data.agent, data.status);
                break;
            case 'message':
                appendAgentMessage(data.agent, data.text);
                break;
            case 'round':
                let markerText = `=== ROUND ${data.number} ===`;
                if (data.number === 'Conclusion') {
                    markerText = `=== CONCLUSION ===`;
                }
                appendSystemMessage(markerText, true);
                break;
            case 'error':
                appendSystemMessage(`ERROR: ${data.message}`);
                closeConnection();
                break;
            case 'finished':
                appendSystemMessage('Simulation sequence complete.');
                closeConnection();
                break;
        }
    };
    
    ws.onerror = (err) => {
        appendSystemMessage('CONNECTION ERROR DETECTED.');
        closeConnection();
    };
    
    ws.onclose = () => {
        closeConnection();
    };
});

function closeConnection() {
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.close();
    }
    sysStatus.classList.remove('active');
    statusText.textContent = 'STANDBY';
    startBtn.disabled = false;
    startBtn.querySelector('span').textContent = 'INITIALIZE SIMULATION';
    topicInput.disabled = false;
    
    // Reset all agents
    ['Moderator', 'Agent Alpha', 'Agent Beta'].forEach(a => updateAgentStatus(a, 'idle'));
}

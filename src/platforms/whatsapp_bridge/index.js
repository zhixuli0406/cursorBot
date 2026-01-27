/**
 * WhatsApp Web.js Bridge for CursorBot
 * 
 * Provides HTTP API to interact with WhatsApp Web
 * 
 * Environment variables:
 * - PORT: HTTP server port (default: 3000)
 * - SESSION_PATH: Session data path (default: .whatsapp_session)
 * - HEADLESS: Run Chrome headless (default: true)
 */

const { Client, LocalAuth, MessageMedia } = require('whatsapp-web.js');
const express = require('express');
const qrcode = require('qrcode');
const fs = require('fs');
const path = require('path');

// Configuration
const PORT = process.env.PORT || 3000;
const SESSION_PATH = process.env.SESSION_PATH || '.whatsapp_session';
const HEADLESS = process.env.HEADLESS !== 'false';

// Express app
const app = express();
app.use(express.json({ limit: '50mb' }));

// State
let clientStatus = 'disconnected';
let currentQR = '';
let messageQueue = [];
const MAX_QUEUE_SIZE = 100;

// WhatsApp client
const client = new Client({
    authStrategy: new LocalAuth({
        dataPath: SESSION_PATH,
    }),
    puppeteer: {
        headless: HEADLESS,
        args: [
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
            '--disable-accelerated-2d-canvas',
            '--no-first-run',
            '--no-zygote',
            '--disable-gpu',
        ],
    },
});

// ============================================
// Client Events
// ============================================

client.on('qr', async (qr) => {
    console.log('QR code received');
    clientStatus = 'qr';
    
    // Generate QR code as data URL
    try {
        currentQR = await qrcode.toDataURL(qr);
    } catch (err) {
        console.error('QR code generation error:', err);
        currentQR = qr;
    }
});

client.on('authenticated', () => {
    console.log('Authenticated');
    clientStatus = 'authenticated';
    currentQR = '';
});

client.on('auth_failure', (msg) => {
    console.error('Authentication failure:', msg);
    clientStatus = 'auth_failure';
});

client.on('ready', () => {
    console.log('WhatsApp client ready');
    clientStatus = 'ready';
});

client.on('disconnected', (reason) => {
    console.log('Disconnected:', reason);
    clientStatus = 'disconnected';
});

client.on('message', async (msg) => {
    // Skip status messages
    if (msg.isStatus) return;
    
    // Get chat and contact info
    const chat = await msg.getChat();
    const contact = await msg.getContact();
    
    // Build message object
    const messageData = {
        id: msg.id._serialized,
        chatId: chat.id._serialized,
        sender: msg.from,
        senderName: contact.pushname || contact.name || msg.from,
        content: msg.body,
        timestamp: new Date(msg.timestamp * 1000).toISOString(),
        isGroup: chat.isGroup,
        groupName: chat.isGroup ? chat.name : '',
        mediaType: '',
        mediaUrl: '',
    };
    
    // Handle media
    if (msg.hasMedia) {
        try {
            const media = await msg.downloadMedia();
            messageData.mediaType = media.mimetype.split('/')[0];
            messageData.mediaUrl = `data:${media.mimetype};base64,${media.data}`;
        } catch (err) {
            console.error('Media download error:', err);
        }
    }
    
    // Add to queue
    messageQueue.push(messageData);
    if (messageQueue.length > MAX_QUEUE_SIZE) {
        messageQueue.shift();
    }
    
    console.log(`Message from ${messageData.senderName}: ${messageData.content.substring(0, 50)}`);
});

// ============================================
// HTTP Routes
// ============================================

// Status
app.get('/status', (req, res) => {
    res.json({
        status: clientStatus,
        qr: currentQR,
    });
});

// Get QR code as image
app.get('/qr', (req, res) => {
    if (!currentQR) {
        return res.status(404).json({ error: 'No QR code available' });
    }
    
    res.type('html').send(`
        <!DOCTYPE html>
        <html>
        <head><title>WhatsApp QR Code</title></head>
        <body style="display:flex;justify-content:center;align-items:center;height:100vh;margin:0;background:#1a1a1a;">
            <div style="text-align:center;color:white;">
                <h2>Scan with WhatsApp</h2>
                <img src="${currentQR}" style="max-width:400px;"/>
                <p>Open WhatsApp > Settings > Linked Devices > Link a Device</p>
            </div>
        </body>
        </html>
    `);
});

// Get messages
app.get('/messages', (req, res) => {
    const messages = [...messageQueue];
    messageQueue = [];
    res.json({ messages });
});

// Send text message
app.post('/send', async (req, res) => {
    const { chatId, content, quoteMessageId } = req.body;
    
    if (!chatId || !content) {
        return res.status(400).json({ error: 'chatId and content required' });
    }
    
    try {
        const options = {};
        if (quoteMessageId) {
            options.quotedMessageId = quoteMessageId;
        }
        
        await client.sendMessage(chatId, content, options);
        res.json({ success: true });
    } catch (err) {
        console.error('Send error:', err);
        res.status(500).json({ error: err.message });
    }
});

// Send media
app.post('/send-media', async (req, res) => {
    const { chatId, media, mediaType, caption, filename, isVoiceNote } = req.body;
    
    if (!chatId || !media) {
        return res.status(400).json({ error: 'chatId and media required' });
    }
    
    try {
        // Parse base64 media
        const mediaMessage = new MessageMedia(
            mediaType === 'image' ? 'image/png' : 
            mediaType === 'audio' ? 'audio/ogg' : 
            'application/octet-stream',
            media,
            filename
        );
        
        const options = { caption };
        if (isVoiceNote) {
            options.sendAudioAsVoice = true;
        }
        
        await client.sendMessage(chatId, mediaMessage, options);
        res.json({ success: true });
    } catch (err) {
        console.error('Send media error:', err);
        res.status(500).json({ error: err.message });
    }
});

// Get chats
app.get('/chats', async (req, res) => {
    try {
        const chats = await client.getChats();
        const chatList = chats.map(chat => ({
            id: chat.id._serialized,
            name: chat.name,
            isGroup: chat.isGroup,
            participants: chat.isGroup ? chat.participants?.map(p => p.id._serialized) : [],
        }));
        res.json({ chats: chatList });
    } catch (err) {
        console.error('Get chats error:', err);
        res.status(500).json({ error: err.message });
    }
});

// Get contact
app.get('/contact/:chatId', async (req, res) => {
    try {
        const contact = await client.getContactById(req.params.chatId);
        res.json({
            id: contact.id._serialized,
            name: contact.pushname || contact.name || contact.number,
            number: contact.number,
        });
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
});

// ============================================
// Start
// ============================================

app.listen(PORT, () => {
    console.log(`WhatsApp bridge running on port ${PORT}`);
});

client.initialize();

// Graceful shutdown
process.on('SIGINT', async () => {
    console.log('Shutting down...');
    await client.destroy();
    process.exit(0);
});

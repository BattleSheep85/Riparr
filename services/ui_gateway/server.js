const express = require('express');
const redis = require('redis');
const cors = require('cors');

const app = express();
app.use(cors());
app.use(express.json());
app.use(express.static('public'));

const PORT = process.env.UI_PORT || 8080;
const ENABLE_UI = process.env.ENABLE_UI !== 'false';

if (!ENABLE_UI) {
  console.log('UI Gateway disabled');
  process.exit(0);
}

// Redis client
const redisClient = redis.createClient({
  host: process.env.REDIS_HOST || 'redis',
  port: process.env.REDIS_PORT || 6379,
});

// Streams to subscribe
const streams = [
  'drive_events',
  'rip.start',
  'rip.progress',
  'rip.complete',
  'enhance.start',
  'enhance.progress',
  'enhance.complete',
  'transcode.start',
  'transcode.progress',
  'transcode.complete',
  'metadata.start',
  'metadata.complete',
  'blackhole.complete',
  'logs'
];

// SSE clients
let clients = [];

// Function to send SSE
function sendSSE(data) {
  clients.forEach(client => {
    client.res.write(`data: ${JSON.stringify(data)}\n\n`);
  });
}

// Subscribe to Redis streams using XREAD
async function subscribeToStreams() {
  let lastIds = streams.reduce((acc, stream) => {
    acc[stream] = '0';
    return acc;
  }, {});

  while (true) {
    try {
      const result = await redisClient.xRead(
        redis.commandOptions({ isolated: true }),
        streams.map(stream => ({ key: stream, id: lastIds[stream] })),
        { count: 10, block: 5000 }
      );

      if (result) {
        result.forEach(({ name, messages }) => {
          messages.forEach(({ id, message }) => {
            lastIds[name] = id;
            sendSSE({ channel: name, id, ...message });
          });
        });
      }
    } catch (err) {
      console.error('Error reading streams:', err);
    }
  }
}

redisClient.on('ready', () => {
  console.log('Connected to Redis');
  subscribeToStreams();
});

// Function to parse messages
function parseMessage(message) {
  try {
    return JSON.parse(message);
  } catch (e) {
    return { message };
  }
}

// SSE endpoint
app.get('/api/events', (req, res) => {
  res.writeHead(200, {
    'Content-Type': 'text/event-stream',
    'Cache-Control': 'no-cache',
    'Connection': 'keep-alive',
    'Access-Control-Allow-Origin': '*',
  });

  const client = { res };
  clients.push(client);

  req.on('close', () => {
    clients = clients.filter(c => c !== client);
  });
});

// REST endpoints for job control
app.post('/api/jobs/:id/pause', async (req, res) => {
  const jobId = req.params.id;
  try {
    await redisClient.xAdd('control', '*', { action: 'pause', jobId });
    res.json({ status: 'paused', jobId });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.post('/api/jobs/:id/cancel', async (req, res) => {
  const jobId = req.params.id;
  try {
    await redisClient.xAdd('control', '*', { action: 'cancel', jobId });
    res.json({ status: 'canceled', jobId });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.post('/api/services/:service/toggle', async (req, res) => {
  const service = req.params.service;
  try {
    await redisClient.xAdd('control', '*', { action: 'toggle', service });
    res.json({ status: 'toggled', service });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.listen(PORT, () => {
  console.log(`UI Gateway listening on port ${PORT}`);
});
const express = require('express');
const redis = require('redis');
const cors = require('cors');

const app = express();
app.use(cors());
app.use(express.json());

const PORT = process.env.LOG_STREAM_PORT || 8081;
const LOG_LEVEL = process.env.LOG_LEVEL || 'info';
const REDIS_LOG_STREAM = process.env.REDIS_LOG_STREAM || 'logs';
const REDIS_HOST = process.env.REDIS_HOST || 'redis';
const REDIS_PORT = process.env.REDIS_PORT || 6379;

// Severity levels
const levels = { debug: 0, info: 1, warn: 2, error: 3 };
const minLevel = levels[LOG_LEVEL] || 1;

// Redis client
const redisClient = redis.createClient({
  host: REDIS_HOST,
  port: REDIS_PORT,
});

// SSE clients
let clients = [];

// Send SSE
function sendSSE(data) {
  clients.forEach(client => {
    client.res.write(`data: ${JSON.stringify(data)}\n\n`);
  });
}

// Subscribe to stream
async function subscribeToLogs() {
  let lastId = '0';
  while (true) {
    try {
      const result = await redisClient.xRead(
        redis.commandOptions({ isolated: true }),
        [{ key: REDIS_LOG_STREAM, id: lastId }],
        { count: 10, block: 5000 }
      );
      if (result) {
        result.forEach(({ name, messages }) => {
          messages.forEach(({ id, message }) => {
            lastId = id;
            sendSSE(message);
          });
        });
      }
    } catch (err) {
      console.error('Error reading logs:', err);
    }
  }
}

redisClient.on('ready', () => {
  console.log('Connected to Redis');
  subscribeToLogs();
});

// POST /api/logs
app.post('/api/logs', async (req, res) => {
  try {
    const log = req.body;
    const jobId = req.headers['x-job-id'] || log.job_id || 'unknown';
    const severity = log.level || 'info';
    if (levels[severity] < minLevel) {
      return res.status(200).json({ status: 'filtered' });
    }
    const taggedLog = {
      ...log,
      job_id: jobId,
      severity,
      timestamp: new Date().toISOString()
    };
    await redisClient.xAdd(REDIS_LOG_STREAM, '*', taggedLog);
    res.status(200).json({ status: 'logged' });
  } catch (err) {
    console.error('Error logging:', err);
    res.status(500).json({ error: err.message });
  }
});

// GET /api/logs/stream
app.get('/api/logs/stream', (req, res) => {
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

// GET /api/logs for replay
app.get('/api/logs', async (req, res) => {
  try {
    const logs = await redisClient.xRange(REDIS_LOG_STREAM, '-', '+');
    const formatted = logs.map(([id, data]) => ({ id, ...data }));
    res.json(formatted);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.listen(PORT, () => {
  console.log(`Log Stream Service listening on port ${PORT}`);
});
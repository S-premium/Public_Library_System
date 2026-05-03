const express = require('express');
const https = require('https');
const fs = require('fs');
const { createProxyMiddleware } = require('http-proxy-middleware');

const app = express();

app.use('/', createProxyMiddleware({
  target: 'http://127.0.0.1:5000',
  changeOrigin: true,
}));

const options = {
  key: fs.readFileSync('key.pem'),
  cert: fs.readFileSync('cert.pem'),
};

https.createServer(options, app).listen(443, () => {
  console.log('HTTPS server running on https://localhost');
});
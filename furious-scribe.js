var net = require('net');
var http = require('http');
var log_module = require('log');
var uuid = require('uuid');
var fs = require('fs');
var spawn = require('child_process').spawn;

var config = require('./config.json');


function getUntilReady(url, callback) {
    http.get(url,function (res) {
        if (res.statusCode == 200)
            callback();
        else {
            console.warn("Got " + res.statusCode + " from [" + url + "]");
            setTimeout(function () {
                getUntilReady(url, callback);
            }, config.testRetryFrequency);
        }
    }).on('error', function (e) {
            console.error("Got error waiting for [" + url + "]: " + e.message);
            setTimeout(function () {
                getUntilReady(url, callback);
            }, config.testRetryFrequency);
        });
}


function runProxy(proxy) {
    proxy.clientHandler = net.createServer(function (clientSocket) {
        var log = new log_module('info', fs.createWriteStream(proxy.serverHost+'.'+proxy.serverPort+'.'+uuid.v4()+'.log'));
        log.info('Received connection from '+clientSocket.remoteAddress+':'+clientSocket.remotePort);
        var serverSocket = null;
        var bufferedData = [];
        serverSocket = new net.Socket();
        serverSocket.connect(parseInt(proxy.serverPort), proxy.serverHost, function () {
            proxy.started = true;
            if (bufferedData.length > 0) {
                var msg = Buffer.concat(bufferedData);
                serverSocket.write(msg);
                console.info("Sent " + msg.length + " bytes of buffered data");
                bufferedData = [];
            }
            serverSocket.on("data", function (data) {
                var response = data.toString();
                if (response.substring(0, 5) == 'HTTP/') {
                    log.info('Response: '+response.split(/\r?\n/)[0].trim())
                }
                clientSocket.write(data);
                log.info('Passed '+data.length+' bytes of data from server to client');
            });
            serverSocket.on('end', function () {
                log.info("Server hung up");
                clientSocket.end();
            });
            serverSocket.on('disconnect', function () {
                log.info("Server lost");
                clientSocket.destroy();
            });
        });
        clientSocket.on('data', function (msg) {
            var lines = msg.toString().split(/\r?\n/);
            if (lines.length > 0) {
                var header = lines[0];
                var header_parts = header.split(/\s+/);
                var verb = header_parts[0].toUpperCase();
                if (header_parts.length == 3 &&
                    (verb == 'GET' ||
                     verb == 'HEAD' ||
                     verb == 'POST' ||
                     verb == 'PUT' ||
                     verb == 'DELETE' ||
                     verb == 'TRACE' ||
                     verb == 'CONNECT' ||
                     verb == 'OPTIONS')) {
                    log.info('Request: '+verb+' '+header_parts[1].trim());
                }
            }
            serverSocket.write(msg);
            log.info('Passed '+msg.length+' bytes of data from client to server');
        });
        clientSocket.on('end', function () {
            log.info("Client hung up");
            serverSocket.end();
        });
        clientSocket.on('disconnect', function () {
            log.info("Client lost");
            serverSocket.destroy();
        });
    });

    proxy.clientHandler.listen(proxy.clientPort);
}

function runProxies() {
    for (var i in config.proxies) {
        if (config.proxies.hasOwnProperty(i)) {
            var proxy = config.proxies[i];
            runProxy(proxy);
        }
    }
}

runProxies();
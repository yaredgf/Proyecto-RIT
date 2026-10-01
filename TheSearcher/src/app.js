const express = require('express');
const app = express();
const http = require('http');
const fs = require('fs');
const back = require('./backend.js');
//import {back} from './backend.js';

const hostname = '127.0.0.1';
const port = 3000;

app.use(express.json()); 
app.use(express.urlencoded({ extended: true })); 


fs.readFile('./pagina/TheSearcher.html', (err, html) => {
	if(err)
	{
		throw err;
	}

	app.get('/', (req, res) => {
		res.statusCode = 200;
		res.setHeader('Content-type','text/html');
		res.write(html);
		res.end;
	});

	// Handle the POST request

	// todos los gets
	app.post('/ObtenerProposiciones', (req, res) => { back.ObtenerProposiciones(req, res)});

	app.post('/ObtenerProposicionesAbiertas', (req, res) => { back.ObtenerProposicionesAbiertas(req, res)});

	app.post('/ValidarPass', (req, res) => { back.ValidarPass(req, res)});

	app.post('/ObtenerUsuario', (req, res) => { back.ObtenerUsuario(req, res)});

	app.post('/ObtenerProposicionesPropias', (req, res) => { back.ObtenerProposicionesPropias(req, res)});

	app.post('/CrearProposicion', (req, res) => { back.CrearProposicion(req, res)});

	app.post('/UsernameExiste', (req, res) => { back.UsernameExiste(req, res)});

	app.post('/xd', (req, res) => { back.Saludar(req, res)});

	app.post('/labd', (req, res) => { back.LaBase(req, res)});
	
	app.post('/omg', (req, res) => {
		
		console.log('Received data:', req.body.msj);

		res.status(201).json({
			message: 'Se ha recibido '+req.body.msj+' en el metodo "omg"'
		});
	});

	app.listen(port, hostname, () => {
		console.log('El server está ON');
		console.log('Las rocas hacen silencio porque el puerto "'+port+'" escucha');
	});
});
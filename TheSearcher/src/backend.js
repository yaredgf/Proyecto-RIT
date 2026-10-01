
module.exports ={
    Saludar: (req, res) => {
        console.log('Received data:', req.body.msj);
        res.status(201).json({
            message: 'Se ha recibido '+req.body.msj+' en el metodo "xd"'
        });
    },
    LaBase: async (req, res) => {
        let query = "Select 2 + 2 as homla";
        const valor = await bd.Ejecutar(query);
        console.dir(valor);
        res.status(201).json({
            message: 'Se ha recibido '+valor[0].homla
        });
    },
    ObtenerProposiciones: async (req, res) => {
        let query = "EXEC sp_ObtenerProposiciones "+req.body.num;
        const valor = await bd.Ejecutar(query);
        console.dir(valor);
        res.status(201).json({
            propositions: valor
        });
    },
    ObtenerProposicionesAbiertas: async (req, res) => {
        let query = "EXEC sp_ObtenerProposicionesAbiertas "+req.body.num;
        const valor = await bd.Ejecutar(query);
        console.dir(valor);
        res.status(201).json({
            propositions: valor
        });
    },
    ValidarPass: async (req, res) => {
        let query = "EXEC sp_ValidarPass '"+req.body.email+"', '"+req.body.pass+"'";
        const valor = await bd.Ejecutar(query);
        console.dir(valor);
        res.status(201).json({
            id: valor
        });
    },
    ObtenerUsuario: async (req, res) => {
        let query = "EXEC sp_ObtenerUsuario "+req.body.id;
        const valor = await bd.Ejecutar(query);
        console.dir(valor);
        res.status(201).json({
            usuario: valor
        });
    },
    ObtenerProposicionesPropias: async (req, res) => {
        let query = "EXEC sp_ObtenerProposicionesPropias "+req.body.id;
        const valor = await bd.Ejecutar(query);
        console.dir(valor);
        res.status(201).json({
            propositions: valor
        });
    },
    CrearProposicion: async (req, res) => {
        let query = `EXEC sp_CrearProposicion
        @title = '${req.body.title}',
        @description = '${req.body.description}',
        @votingStart = '${req.body.votingStart}',
        @votingEnd = '${req.body.votingEnd}',
        @challengeStart = '${req.body.challengeStart}',
        @challengeEnd = '${req.body.challengeEnd}',
        @externalLink = '${req.body.externalLink}',
        @createdBy = ${req.body.createdBy},
        @targetUser = ${req.body.targetUser}
        `;

        const valor = await bd.Ejecutar(query);
        console.dir(valor);
        res.status(201).json({
            propositions: valor
        });
    },
    UsernameExiste: async (req, res) => {
        let query = "EXEC sp_UsernameExiste "+req.body.user;
        const valor = await bd.Ejecutar(query);
        console.dir(valor);
        res.status(201).json({
            id: valor
        });
    }
};



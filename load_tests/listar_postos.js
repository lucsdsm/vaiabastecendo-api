import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
    stages: [
        { duration: '15s', target: 20 }, // Sobe para 20 usuários simulados
        { duration: '30s', target: 20 }, // Mantém o estresse do cálculo espacial
        { duration: '10s', target: 0 },  // Desliga os usuários
    ],
    thresholds: {
        http_req_failed: ['rate<0.01'], 
        // Cálculos do PostGIS são mais pesados, 
        // então aceitamos que 95% das respostas cheguem em até 800ms
        http_req_duration: ['p(95)<800'], 
    },
};

export default function () {
    // 1. Pegamos o IP da linha de comando de forma segura
    const ip = __ENV.ORACLE_IP;

    if (!ip) {
        console.error("ERRO: Você esqueceu de passar o IP. Use: k6 run -e ORACLE_IP=xxx.xxx.xxx.xxx script.js");
        return;
    }

    // 2. Coordenadas de Natal para forçar o PostGIS a calcular as distâncias
    const lat = '-5.8126';
    const lng = '-35.2051';
    
    // 3. Montamos a URL batendo no seu ModelViewSet
    const url = `http://${ip}:8000/api/postos/?lat=${lat}&lng=${lng}`;

    const params = {
        headers: {
            'Content-Type': 'application/json',
            // Descomente e adicione um token se essa rota for protegida por autenticação:
            // 'Authorization': 'Token SEU_TOKEN_AQUI',
        },
    };

    // 4. Disparo
    const res = http.get(url, params);

    // 5. Validação
    check(res, {
        'Retornou 200 OK': (r) => r.status === 200,
        'Retornou array de postos': (r) => r.body.includes('['),
    });

    sleep(1);
}
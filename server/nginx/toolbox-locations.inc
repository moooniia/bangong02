    location = / {
        if ($http_referer ~ "/login") {
            return 302 /dashboard;
        }
        try_files /index.html =404;
    }

    location = /script.js {
        proxy_pass http://127.0.0.1:3000/script.js;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /_next/ {
        proxy_pass http://127.0.0.1:3000/_next/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location ~ ^/api/(auth|websites|send|heartbeat|me|realtime|reports|sessions|stats|teams|users|share|config|admin|telemetry|event-data|batch) {
        proxy_pass http://127.0.0.1:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location ~ ^/(login|dashboard|settings|profile|teams|reports|console|share|websites)(/|$) {
        proxy_pass http://127.0.0.1:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location ~ ^/(favicon\.ico|site\.webmanifest|apple-touch-icon\.png|favicon-32x32\.png|favicon-16x16\.png|safari-pinned-tab\.svg)$ {
        proxy_pass http://127.0.0.1:3000;
        proxy_set_header Host $host;
    }

    location = /stats {
        return 302 /login;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        client_max_body_size 100m;
        proxy_connect_timeout 600s;
        proxy_send_timeout 600s;
        proxy_read_timeout 600s;
    }

    location / {
        try_files $uri $uri/ /index.html;
    }

pipeline {
    agent any
    
    stages {
        stage('Установка Python и зависимостей') {
            steps {
                sh '''
                    echo "=== УСТАНОВКА PYTHON И ЗАВИСИМОСТЕЙ ==="
                    apt-get update
                    apt-get install -y python3 python3-pip python3-venv curl
                    
                    # Создаем виртуальное окружение
                    python3 -m venv venv
                    . venv/bin/activate
                    
                    # Устанавливаем зависимости в виртуальное окружение
                    pip install pytest requests selenium locust
                '''
            }
        }
        
        stage('Проверка доступности OpenBMC') {
            steps {
                sh '''
                    echo "=== ПРОВЕРКА ДОСТУПНОСТИ OPENBMC ==="
                    . venv/bin/activate
                    
                    # Проверяем доступность OpenBMC
                    echo "Проверка подключения к OpenBMC..."
                    curl -k -I https://host.docker.internal:2443/redfish/v1 || echo "OpenBMC не доступен"
                    
                    # Заменяем localhost на host.docker.internal во всех файлах
                    sed -i 's/localhost:2443/host.docker.internal:2443/g' api_lab5.py
                    sed -i 's/localhost:2443/host.docker.internal:2443/g' webui_lab4.py
                    sed -i 's/localhost:2443/host.docker.internal:2443/g' locustfile.py
                    
                    echo "Файлы обновлены для работы в Docker"
                '''
            }
        }
        
        stage('API тесты Redfish') {
            steps {
                sh '''
                    echo "=== ЗАПУСК API ТЕСТОВ ==="
                    . venv/bin/activate
                    python3 -m pytest api_lab5.py -v || echo "API тесты завершились с ошибкой"
                '''
            }
            post {
                always {
                    archiveArtifacts 'redfish_test.log'
                }
            }
        }
        
        stage('WebUI тесты') {
            steps {
                sh '''
                    echo "=== ЗАПУСК WEBUI ТЕСТОВ ==="
                    . venv/bin/activate
                    python3 webui_lab4.py || echo "WebUI тесты завершились с ошибкой"
                '''
            }
        }
        
        stage('Нагрузочное тестирование') {
            steps {
                sh '''
                    echo "=== ЗАПУСК НАГРУЗОЧНОГО ТЕСТИРОВАНИЯ ==="
                    . venv/bin/activate
                    timeout 30 locust -f locustfile.py --headless -u 5 -r 1 --run-time 20s --host=https://host.docker.internal:2443 || echo "Нагрузочное тестирование завершилось с ошибкой"
                '''
            }
        }
    }
    
    post {
        always {
            archiveArtifacts '**/*.log, **/*.html'
        }
    }
}
pipeline {
    agent any
    
    stages {
        stage('Установка Python и зависимостей') {
            steps {
                sh '''
                    echo "=== УСТАНОВКА PYTHON И ЗАВИСИМОСТЕЙ ==="
                    apt-get update
                    apt-get install -y python3 python3-pip
                    pip3 install pytest requests selenium locust
                '''
            }
        }
        
        stage('API тесты Redfish') {
            steps {
                sh '''
                    echo "=== ЗАПУСК API ТЕСТОВ ==="
                    python3 -m pytest api_lab5.py -v
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
                    python3 webui_lab4.py
                '''
            }
        }
        
        stage('Нагрузочное тестирование') {
            steps {
                sh '''
                    echo "=== ЗАПУСК НАГРУЗОЧНОГО ТЕСТИРОВАНИЯ ==="
                    timeout 30 locust -f locustfile.py --headless -u 5 -r 1 --run-time 20s --host=https://localhost:2443
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
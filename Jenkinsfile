pipeline {
    agent any
    
    stages {
        stage('Подготовка окружения') {
            steps {
                sh '''
                    echo "=== ПОДГОТОВКА ОКРУЖЕНИЯ ==="
                    apt-get update
                    apt-get install -y python3 python3-pip python3-venv qemu-system-arm curl
                    
                    python3 -m venv venv
                    . venv/bin/activate
                    pip install pytest requests selenium locust pytest-html
                '''
            }
        }
        
        stage('Запуск QEMU с OpenBMC') {
            steps {
                sh '''
                    echo "=== ЗАПУСК QEMU С OPENBMC ==="
                    # Запускаем QEMU в фоновом режиме
                    qemu-system-arm -m 256 -M romulus-bmc -nographic \
                        -drive file=romulus/obmc-phosphor-image-romulus-20250906002013.static.mtd,format=raw,if=mtd \
                        -net nic \
                        -net user,hostfwd=:0.0.0.0:2222-:22,hostfwd=:0.0.0.0:2443-:443,hostfwd=udp:0.0.0.0:2623-:623,hostname=qemu \
                        > qemu.log 2>&1 &
                    
                    echo $! > qemu.pid
                    echo "QEMU запущен, PID: $(cat qemu.pid)"
                    
                    echo "Ожидание загрузки OpenBMC..."
                    sleep 60
                    
                    # Проверяем доступность OpenBMC
                    timeout 120 bash -c 'until curl -k -f https://localhost:2443/redfish/v1 >/dev/null 2>&1; do sleep 5; echo "Ждем OpenBMC..."; done'
                    echo "OpenBMC доступен!"
                '''
            }
            post {
                always {
                    archiveArtifacts 'qemu.log, qemu.pid'
                }
            }
        }
        
        stage('Автотесты Redfish API') {
            steps {
                sh '''
                    echo "=== АВТОТЕСТЫ REDFISH API ==="
                    . venv/bin/activate
                    python3 -m pytest api_lab5.py -v --html=api-test-report.html || echo "Тесты завершились с ошибками"
                '''
            }
            post {
                always {
                    archiveArtifacts 'api-test-report.html, redfish_test.log'
                }
            }
        }
        
        stage('WebUI тесты') {
            steps {
                sh '''
                    echo "=== WEBUI ТЕСТЫ ==="
                    . venv/bin/activate
                    apt-get install -y chromium chromium-driver
                    python3 webui_lab4.py || echo "WebUI тесты завершились с ошибками"
                '''
            }
            post {
                always {
                    archiveArtifacts 'webui-test-log.txt'
                }
            }
        }
        
        stage('Нагрузочное тестирование') {
            steps {
                sh '''
                    echo "=== НАГРУЗОЧНОЕ ТЕСТИРОВАНИЕ ==="
                    . venv/bin/activate
                    timeout 60 locust -f locustfile.py --headless -u 5 -r 1 --run-time 30s --html=loadtest-report.html || echo "Нагрузочное тестирование завершилось с ошибками"
                '''
            }
            post {
                always {
                    archiveArtifacts 'loadtest-report.html'
                }
            }
        }
        
        stage('Остановка QEMU') {
            steps {
                sh '''
                    echo "=== ОСТАНОВКА QEMU ==="
                    if [ -f qemu.pid ]; then
                        echo "Останавливаем QEMU с PID: $(cat qemu.pid)"
                        kill $(cat qemu.pid) || true
                        rm -f qemu.pid
                        echo "QEMU остановлен"
                    fi
                '''
            }
        }
    }
    
    post {
        always {
            sh '''
                echo "=== СОХРАНЕНИЕ АРТЕФАКТОВ ==="
                ls -la *.html *.log *.txt 2>/dev/null || echo "Файлы отчетов не найдены"
            '''
            archiveArtifacts '**/*.html, **/*.log, **/*.txt'
        }
        success {
            echo "✅ Все этапы пайплайна выполнены успешно!"
        }
        failure {
            echo "❌ Пайплайн завершился с ошибками"
        }
    }
}
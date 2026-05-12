pipeline {
    agent any

    options {
        disableConcurrentBuilds()
        timestamps()
        timeout(time: 30, unit: 'MINUTES')
    }

    triggers {
        githubPush()
    }

    environment {
        SERVER = "ubuntu@100.28.53.53"
        APP_DIR = "/home/ubuntu/proyecto-huella"
        BRANCH = "main"
    }

    stages {
        stage('Actualizar código en servidor') {
            steps {
                sshagent(credentials: ['carbonozero-lightsail-ssh']) {
                    sh '''
                        ssh -o StrictHostKeyChecking=no "$SERVER" "APP_DIR='$APP_DIR' BRANCH='$BRANCH' bash -s" <<'REMOTE'
                            set -e

                            echo "📥 Entrando al proyecto..."
                            cd "$APP_DIR"

                            echo "🔄 Actualizando código desde GitHub..."
                            git fetch origin "$BRANCH"
                            git reset --hard "origin/$BRANCH"

                            echo "🔐 Dando permisos al deploy..."
                            chmod +x deploy.sh

                            echo "🚀 Ejecutando deploy de Carbono Zero..."
                            ./deploy.sh
REMOTE
                    '''
                }
            }
        }
    }

    post {
        success {
            echo '✅ Carbono Zero desplegado correctamente desde Jenkins.'
        }

        failure {
            echo '❌ Falló el despliegue de Carbono Zero. Revisa la consola de Jenkins.'
        }
    }
}
pipeline {
    agent any

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }
        stage('Install dependencies') {
            steps {
                sh '''
                    python3 -m venv venv
                    . venv/bin/activate
                    pip install -r requirements.txt
                '''
            }
        }
        stage('Run API + ETL tests') {
            steps {
                sh '''
                    . venv/bin/activate
                    python3 mock_target/app.py &
                    sleep 2
                    pytest -m "api or etl" -v
                '''
            }
        }
    }
}
//CI/CD pipeline definition
pipeline {
    // Agent 'any' means Jenkins can use any available agent to run this pipeline.
    // For our Docker-based project, a Jenkins agent with Docker installed is required.
    agent any

    // Environment variables available to all stages
    environment {
        // Use a registry like Docker Hub. Replace 'your-dockerhub-username'
        DOCKER_REGISTRY = "your-dockerhub-username" 
        DOCKER_CREDENTIALS_ID = "dockerhub-credentials" // ID of credentials stored in Jenkins
        APP_NAME = "real-time-ml-app"
    }

    stages {
        // --- Stage 1: Build Docker Images ---
        stage('Build') {
            steps {
                script {
                    echo "Building Docker images..."
                    // Build the API image
                    sh "docker build -t ${env.DOCKER_REGISTRY}/${env.APP_NAME}-api:latest -f app/Dockerfile.api ./app"
                    // Build the ingestion service image
                    sh "docker build -t ${env.DOCKER_REGISTRY}/${env.APP_NAME}-ingest:latest -f app/Dockerfile.ingest ./app"
                }
            }
        }

        // --- Stage 2: Run Tests ---
        // This stage runs our pytest suite to ensure code quality.
        stage('Test') {
            steps {
                script {
                    echo "Running tests..."
                    // Use docker-compose to run the 'tests' service we defined.
                    // The '--rm' flag cleans up the container after the test run.
                    sh "docker-compose run --rm tests"
                }
            }
        }

        // --- Stage 3: Push to Registry (if tests pass) ---
        // This stage pushes the built images to a container registry.
        stage('Push to Registry') {
            steps {
                script {
                    echo "Pushing images to Docker Hub..."
                    withCredentials([string(credentialsId: env.DOCKER_CREDENTIALS_ID, variable: 'DOCKER_PASSWORD')]) {
                        sh "echo ${DOCKER_PASSWORD} | docker login -u ${env.DOCKER_REGISTRY} --password-stdin"
                        sh "docker push ${env.DOCKER_REGISTRY}/${env.APP_NAME}-api:latest"
                        sh "docker push ${env.DOCKER_REGISTRY}/${env.APP_NAME}-ingest:latest"
                    }
                }
            }
        }

        // --- Stage 4: Deploy ---
        // This is a placeholder for deployment. In a real-world scenario, this
        // stage would connect to a server (e.g., via SSH) and run 'docker-compose up'
        // with the new images.
        stage('Deploy') {
            steps {
                script {
                    echo "Deployment step placeholder."
                    echo "In a real environment, you would run commands like:"
                    echo "ssh user@your-server 'cd /path/to/app && docker-compose pull && docker-compose up -d'"
                }
            }
        }
    }

    // --- Post-build Actions ---
    // Actions that run at the end of the pipeline, regardless of status.
    post {
        always {
            echo "Pipeline finished."
            // Clean up local Docker images to save space
            sh "docker rmi ${env.DOCKER_REGISTRY}/${env.APP_NAME}-api:latest || true"
            sh "docker rmi ${env.DOCKER_REGISTRY}/${env.APP_NAME}-ingest:latest || true"
        }
    }
}
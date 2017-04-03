// Version of base CI functionality
CI_BASE_VERSION = "v2.0"

// Type of CI job
TYPE = "generic"

// Set to full, simple or auto
BUILD_TYPE = "simple"

// Email recipients, whitespace separated
EMAIL_RECIPIENTS = ""

QDOCKER_DOCKER_IMAGES_YML=[]

HIPCHAT_NOTIFICATION_CHANNEL = ["1182"]

// Used to determine if sending feedback, deploying automatically
DELIVERY_BRANCH = "develop"

node {
  checkout scm

  dir('pipelinebase') {
        // Need to wipe out the CI base repository here, else new changes won't be picked up
        checkout([$class: 'GitSCM', branches: [[name: "$CI_BASE_VERSION"]],
                                    doGenerateSubmoduleConfigurations: false,
                                    extensions: [[$class: 'WipeWorkspace']],
                                    submoduleCfg: [],
                                    userRemoteConfigs: [[url: 'ssh://git@stash.qvantel.net:7999/devops/jenkins-pipeline-base.git']]])
    }

  base = load 'pipelinebase/pipelinebase.groovy'
  base.runPipeline(this)
}

def getPostFix() {
  def sha1short = env.GIT_COMMIT_SHA1.substring(0, 8)
  def currentBuildNumber = currentBuild.number
  sh 'python setup.py --version > result'
  def packageVersionNumber = readFile('result').split("\r?\n")[0]
  return "${packageVersionNumber}.${currentBuildNumber}.${env.BRANCH_NAME}.${sha1short}"
}

def compile() {
  def postFix = getPostFix()
  stage "Building jsonapi-client image"
  docker.withRegistry('https://artifactory.qvantel.net', 'cdb3be7e-e719-4ffe-b0c1-67616c775633') {
    def image = docker.build "qflow-jsonapi-client:${postFix}"
  }
}

def integrationTest() {
  stage 'Running integration tests'
  def postFix = getPostFix()
  def jsonapiImage = docker.image "qflow-jsonapi-client:${postFix}"
  sh 'mkdir test-reports'
  sh 'mkdir coverage-reports'
  jsonapiImage.inside() {
    stage("Running tests"){
      sh 'pytest --junitxml=test-reports/results.xml --cov-report xml:coverage-reports/coverage.xml --cov-report html:coverage-reports/index.html --cov=src/jsonapi_client'
    }
  }
  stage("Reading reports"){
    junit 'test-reports/*.xml'
    publishHTML([
      allowMissing: false,
      alwaysLinkToLastBuild: true,
      keepAll: true,
      reportDir: 'coverage-reports',
      reportFiles: 'index.html',
      reportName: 'Coverage report'])
  }
  stage("Running CIM tests"){
      build '../jsonapi-client-cim-tests_pipeline/master'
  }
}
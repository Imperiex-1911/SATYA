import * as cdk from 'aws-cdk-lib';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import * as sqs from 'aws-cdk-lib/aws-sqs';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as ssm from 'aws-cdk-lib/aws-ssm';
import { Construct } from 'constructs';

export class SatyaStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // ─────────────────────────────────────────────
    // S3 — Media + Reports bucket
    // ─────────────────────────────────────────────
    const mediaBucket = new s3.Bucket(this, 'SatyaMediaBucket', {
      bucketName: `satya-media-${this.account}-${this.region}`,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
      autoDeleteObjects: true,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      encryption: s3.BucketEncryption.S3_MANAGED,
      lifecycleRules: [
        {
          // Raw video + audio: delete after 24 hours
          id: 'delete-raw-24h',
          prefix: 'raw/',
          expiration: cdk.Duration.days(1),
        },
        {
          // Extracted frames: delete after 24 hours
          id: 'delete-frames-24h',
          prefix: 'frames/',
          expiration: cdk.Duration.days(1),
        },
        {
          // Thumbnails: delete after 24 hours
          id: 'delete-thumbnails-24h',
          prefix: 'thumbnails/',
          expiration: cdk.Duration.days(1),
        },
        {
          // Reports: delete after 30 days
          id: 'delete-reports-30d',
          prefix: 'reports/',
          expiration: cdk.Duration.days(30),
        },
      ],
      cors: [
        {
          allowedMethods: [s3.HttpMethods.GET],
          allowedOrigins: ['*'],
          allowedHeaders: ['*'],
          maxAge: 3600,
        },
      ],
    });

    // ─────────────────────────────────────────────
    // DynamoDB — satya-analyses table
    // ─────────────────────────────────────────────
    const analysesTable = new dynamodb.Table(this, 'SatyaAnalysesTable', {
      tableName: 'satya-analyses',
      partitionKey: { name: 'analysis_id', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'created_at', type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
      timeToLiveAttribute: 'ttl',
      pointInTimeRecoverySpecification: { pointInTimeRecoveryEnabled: false },
    });

    // GSI-1: query by user_id
    analysesTable.addGlobalSecondaryIndex({
      indexName: 'user-index',
      partitionKey: { name: 'user_id', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'created_at', type: dynamodb.AttributeType.STRING },
    });

    // GSI-2: query by platform
    analysesTable.addGlobalSecondaryIndex({
      indexName: 'platform-index',
      partitionKey: { name: 'platform', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'created_at', type: dynamodb.AttributeType.STRING },
    });

    // ─────────────────────────────────────────────
    // DynamoDB — satya-trending table
    // ─────────────────────────────────────────────
    const trendingTable = new dynamodb.Table(this, 'SatyaTrendingTable', {
      tableName: 'satya-trending',
      partitionKey: { name: 'date', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'platform_content_id', type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
      timeToLiveAttribute: 'ttl',
    });

    // GSI: query by platform
    trendingTable.addGlobalSecondaryIndex({
      indexName: 'platform-trending-index',
      partitionKey: { name: 'platform', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'detected_at', type: dynamodb.AttributeType.STRING },
    });

    // ─────────────────────────────────────────────
    // SQS — Dead Letter Queues
    // ─────────────────────────────────────────────
    const videoDLQ = new sqs.Queue(this, 'VideoJobsDLQ', {
      queueName: 'satya-video-jobs-dlq',
      retentionPeriod: cdk.Duration.days(7),
    });

    const audioDLQ = new sqs.Queue(this, 'AudioJobsDLQ', {
      queueName: 'satya-audio-jobs-dlq',
      retentionPeriod: cdk.Duration.days(7),
    });

    const textDLQ = new sqs.Queue(this, 'TextJobsDLQ', {
      queueName: 'satya-text-jobs-dlq',
      retentionPeriod: cdk.Duration.days(7),
    });

    // ─────────────────────────────────────────────
    // SQS — Main Job Queues
    // ─────────────────────────────────────────────
    const videoJobsQueue = new sqs.Queue(this, 'VideoJobsQueue', {
      queueName: 'satya-video-jobs',
      visibilityTimeout: cdk.Duration.seconds(300), // 5 min for video processing
      retentionPeriod: cdk.Duration.days(1),
      deadLetterQueue: {
        queue: videoDLQ,
        maxReceiveCount: 3,
      },
    });

    const audioJobsQueue = new sqs.Queue(this, 'AudioJobsQueue', {
      queueName: 'satya-audio-jobs',
      visibilityTimeout: cdk.Duration.seconds(180), // 3 min for audio processing
      retentionPeriod: cdk.Duration.days(1),
      deadLetterQueue: {
        queue: audioDLQ,
        maxReceiveCount: 3,
      },
    });

    const textJobsQueue = new sqs.Queue(this, 'TextJobsQueue', {
      queueName: 'satya-text-jobs',
      visibilityTimeout: cdk.Duration.seconds(60), // 1 min for text analysis
      retentionPeriod: cdk.Duration.days(1),
      deadLetterQueue: {
        queue: textDLQ,
        maxReceiveCount: 3,
      },
    });

    // ─────────────────────────────────────────────
    // IAM — Worker Role (shared by API + workers)
    // ─────────────────────────────────────────────
    const workerRole = new iam.Role(this, 'SatyaWorkerRole', {
      roleName: 'satya-worker-role',
      assumedBy: new iam.CompositePrincipal(
        new iam.ServicePrincipal('ecs-tasks.amazonaws.com'),
        new iam.ServicePrincipal('lambda.amazonaws.com'),
      ),
    });

    // S3 access
    mediaBucket.grantReadWrite(workerRole);

    // DynamoDB access
    analysesTable.grantReadWriteData(workerRole);
    trendingTable.grantReadWriteData(workerRole);

    // SQS access
    videoJobsQueue.grantSendMessages(workerRole);
    videoJobsQueue.grantConsumeMessages(workerRole);
    audioJobsQueue.grantSendMessages(workerRole);
    audioJobsQueue.grantConsumeMessages(workerRole);
    textJobsQueue.grantSendMessages(workerRole);
    textJobsQueue.grantConsumeMessages(workerRole);

    // Bedrock access
    workerRole.addToPolicy(new iam.PolicyStatement({
      actions: ['bedrock:InvokeModel'],
      resources: ['*'],
    }));

    // Translate access
    workerRole.addToPolicy(new iam.PolicyStatement({
      actions: ['translate:TranslateText'],
      resources: ['*'],
    }));

    // CloudWatch Logs
    workerRole.addToPolicy(new iam.PolicyStatement({
      actions: ['logs:CreateLogGroup', 'logs:CreateLogStream', 'logs:PutLogEvents'],
      resources: ['*'],
    }));

    // ─────────────────────────────────────────────
    // SSM Parameters — share config with backend
    // ─────────────────────────────────────────────
    new ssm.StringParameter(this, 'MediaBucketParam', {
      parameterName: '/satya/media-bucket-name',
      stringValue: mediaBucket.bucketName,
    });

    new ssm.StringParameter(this, 'VideoQueueParam', {
      parameterName: '/satya/video-queue-url',
      stringValue: videoJobsQueue.queueUrl,
    });

    new ssm.StringParameter(this, 'AudioQueueParam', {
      parameterName: '/satya/audio-queue-url',
      stringValue: audioJobsQueue.queueUrl,
    });

    new ssm.StringParameter(this, 'TextQueueParam', {
      parameterName: '/satya/text-queue-url',
      stringValue: textJobsQueue.queueUrl,
    });

    // ─────────────────────────────────────────────
    // Outputs
    // ─────────────────────────────────────────────
    new cdk.CfnOutput(this, 'MediaBucketName', {
      value: mediaBucket.bucketName,
      description: 'S3 bucket for media storage',
      exportName: 'SatyaMediaBucketName',
    });

    new cdk.CfnOutput(this, 'AnalysesTableName', {
      value: analysesTable.tableName,
      description: 'DynamoDB table for analyses',
      exportName: 'SatyaAnalysesTableName',
    });

    new cdk.CfnOutput(this, 'VideoQueueUrl', {
      value: videoJobsQueue.queueUrl,
      description: 'SQS queue for video forensic jobs',
      exportName: 'SatyaVideoQueueUrl',
    });

    new cdk.CfnOutput(this, 'AudioQueueUrl', {
      value: audioJobsQueue.queueUrl,
      description: 'SQS queue for audio forensic jobs',
      exportName: 'SatyaAudioQueueUrl',
    });

    new cdk.CfnOutput(this, 'TextQueueUrl', {
      value: textJobsQueue.queueUrl,
      description: 'SQS queue for text analysis jobs',
      exportName: 'SatyaTextQueueUrl',
    });

    new cdk.CfnOutput(this, 'WorkerRoleArn', {
      value: workerRole.roleArn,
      description: 'IAM role ARN for SATYA workers',
      exportName: 'SatyaWorkerRoleArn',
    });
  }
}

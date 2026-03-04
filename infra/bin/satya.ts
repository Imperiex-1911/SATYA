#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import { SatyaStack } from '../lib/satya-stack';

const app = new cdk.App();

new SatyaStack(app, 'SatyaStack', {
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT || '755483013810',
    region: process.env.CDK_DEFAULT_REGION || 'ap-south-1',
  },
  description: 'SATYA — Synthetic Audio & Video Authenticity Platform',
});

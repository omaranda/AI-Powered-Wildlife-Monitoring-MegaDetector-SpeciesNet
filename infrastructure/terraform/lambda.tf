# Camera Trap Species Detection Platform - Lambda Configuration
#
# Copyright (c) 2025 Omar Miranda
# SPDX-License-Identifier: Apache-2.0

# Lambda IAM Role
resource "aws_iam_role" "lambda" {
  name = "${var.project_name}-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })
}

# Lambda IAM Policy
resource "aws_iam_role_policy" "lambda" {
  name = "${var.project_name}-lambda-policy"
  role = aws_iam_role.lambda.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:*"
      },
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject"
        ]
        Resource = "arn:aws:s3:::${var.s3_bucket_name}/*"
      },
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Resource = aws_secretsmanager_secret.db_password.arn
      },
      {
        Effect = "Allow"
        Action = [
          "ec2:CreateNetworkInterface",
          "ec2:DescribeNetworkInterfaces",
          "ec2:DeleteNetworkInterface"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "dynamodb:PutItem",
          "dynamodb:GetItem",
          "dynamodb:UpdateItem"
        ]
        Resource = "arn:aws:dynamodb:${var.aws_region}:*:table/*"
      }
    ]
  })
}

# Lambda Function
resource "aws_lambda_function" "detection_pipeline" {
  function_name = "${var.project_name}-detection-pipeline"
  role          = aws_iam_role.lambda.arn
  handler       = "handler.lambda_handler"
  runtime       = "python3.11"
  timeout       = var.lambda_timeout
  memory_size   = var.lambda_memory

  # Placeholder for code - will be updated by deployment script
  filename         = "lambda_placeholder.zip"
  source_code_hash = filebase64sha256("lambda_placeholder.zip")

  vpc_config {
    subnet_ids         = aws_subnet.public[*].id
    security_group_ids = [aws_security_group.lambda.id]
  }

  environment {
    variables = {
      DB_HOST               = aws_db_instance.main.address
      DB_NAME               = var.db_name
      DB_USER               = var.db_username
      DB_PASSWORD_SECRET_ID = aws_secretsmanager_secret.db_password.id
      MEGADETECTOR_THRESHOLD = "0.6"
      SPECIESNET_THRESHOLD   = "0.5"
    }
  }

  layers = [aws_lambda_layer_version.ml_models.arn]

  tags = {
    Name = "${var.project_name}-detection-pipeline"
  }
}

# Lambda Layer for ML Models (placeholder)
resource "aws_lambda_layer_version" "ml_models" {
  layer_name          = "${var.project_name}-ml-models"
  filename            = "layer_placeholder.zip"
  source_code_hash    = filebase64sha256("layer_placeholder.zip")
  compatible_runtimes = ["python3.11"]

  description = "ML models for MegaDetector and SpeciesNet"
}

# S3 Event Trigger
resource "aws_lambda_permission" "allow_s3" {
  statement_id  = "AllowExecutionFromS3"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.detection_pipeline.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = "arn:aws:s3:::${var.s3_bucket_name}"
}

# CloudWatch Log Group
resource "aws_cloudwatch_log_group" "lambda" {
  name              = "/aws/lambda/${aws_lambda_function.detection_pipeline.function_name}"
  retention_in_days = 30
}

# CloudWatch Alarms for Lambda
resource "aws_cloudwatch_metric_alarm" "lambda_errors" {
  alarm_name          = "${var.project_name}-lambda-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = "300"
  statistic           = "Sum"
  threshold           = "5"
  alarm_description   = "Lambda function errors"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    FunctionName = aws_lambda_function.detection_pipeline.function_name
  }
}

resource "aws_cloudwatch_metric_alarm" "lambda_duration" {
  alarm_name          = "${var.project_name}-lambda-long-duration"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "Duration"
  namespace           = "AWS/Lambda"
  period              = "300"
  statistic           = "Average"
  threshold           = "600000" # 10 minutes in ms
  alarm_description   = "Lambda function taking too long"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    FunctionName = aws_lambda_function.detection_pipeline.function_name
  }
}

# Create placeholder zip files for Terraform
resource "null_resource" "create_placeholders" {
  provisioner "local-exec" {
    command = "touch lambda_placeholder.txt && zip lambda_placeholder.zip lambda_placeholder.txt && zip layer_placeholder.zip lambda_placeholder.txt"
  }
}

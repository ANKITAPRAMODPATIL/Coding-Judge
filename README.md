Online Judge System

Overview

Online Judge System is a web-based coding platform that allows users to solve programming problems, participate in coding contests, track their progress, and improve their problem-solving skills. The platform provides real-time code evaluation, leaderboards, analytics, discussions, and AI-powered assistance to enhance the learning experience.

Features

- User Authentication and Authorization
- Problem Repository with Difficulty Levels and Tags
- Coding Contests and Contest Leaderboards
- Global Leaderboard and Rankings
- Submission History
- Custom Test Case Execution
- Real-Time Code Evaluation
- AI Hint Generation
- AI Code Review
- Discussion Forum
- Performance Analytics
- Profile, XP, Levels, and Badges

Technology Stack

- Django
- Supabase PostgreSQL
- Bootstrap
- JavaScript
- Docker
- Railway

Code Execution Architecture

Submitted code is executed inside isolated Docker containers to ensure secure and reliable code execution.

Workflow

User → Django Backend → Docker Sandbox → Test Case Execution → Verdict

Security Features

- Docker-based Isolation
- Execution Time Limits
- Resource Restrictions
- Secure Sandbox Environment

Supported Verdicts

- Accepted
- Wrong Answer
- Runtime Error
- Time Limit Exceeded
- Compilation Error

AI Features

- AI Hint Generation
- AI Code Review
- Solution Explanation
- Complexity Analysis
- Personalized Recommendations
- Test Case Generation

Deployment

The application is deployed on Railway and uses Supabase PostgreSQL as the production database.

Project Goal

The goal of this project is to provide a complete online coding platform where users can practice problems, participate in contests, improve their programming skills, and receive AI-powered assistance while learning.

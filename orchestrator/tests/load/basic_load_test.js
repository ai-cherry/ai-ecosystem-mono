import http from 'k6/http';
import { check, sleep } from 'k6';
import { Counter, Rate, Trend } from 'k6/metrics';

// Custom metrics
const requestsCounter = new Counter('requests');
const errorRate = new Rate('errors');
const processingTimeTrend = new Trend('processing_time');

// Test configuration
export const options = {
  stages: [
    { duration: '30s', target: 10 }, // Ramp up to 10 users over 30 seconds
    { duration: '1m', target: 100 }, // Ramp up to 100 users over 1 minute
    { duration: '2m', target: 100 }, // Stay at 100 users for 2 minutes
    { duration: '30s', target: 0 }, // Ramp down to 0 users over 30 seconds
  ],
  thresholds: {
    http_req_duration: ['p(95)<2000'], // 95% of requests should complete within 2s
    'http_req_duration{endpoint:process_async}': ['p(95)<3000'], // 95% of async requests should complete within 3s
    errors: ['rate<0.02'], // Error rate should be less than 2%
  },
};

// Test setup
export function setup() {
  console.log('Setting up load test');
  // You could perform setup tasks here, such as creating test data
  return {
    baseUrl: __ENV.BASE_URL || 'http://localhost:8000',
    apiKey: __ENV.API_KEY || 'test-api-key',
  };
}

// Main test function executed for each virtual user
export default function(data) {
  const baseUrl = data.baseUrl;
  const apiKey = data.apiKey;
  
  // Sample payload for the process_async endpoint
  const payload = JSON.stringify({
    task: "Analyze this document for key insights",
    documents: ["document1.txt"],
    options: {
      depth: "medium",
      format: "json"
    }
  });
  
  // Headers for the request
  const headers = {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${apiKey}`,
  };
  
  // Make the POST request to the process_async endpoint
  const startTime = new Date().getTime();
  const response = http.post(`${baseUrl}/api/v1/process_async`, payload, { headers });
  const endTime = new Date().getTime();
  
  // Track metrics
  requestsCounter.add(1);
  processingTimeTrend.add(endTime - startTime);
  
  // Check response
  const checkResult = check(response, {
    'status is 202': (r) => r.status === 202,
    'response has run_id': (r) => JSON.parse(r.body).run_id !== undefined,
  });
  
  // Track errors
  if (!checkResult) {
    errorRate.add(1);
    console.error(`Error in request: ${response.status}, ${response.body}`);
  }
  
  // Add a sleep between requests to simulate real-world usage patterns
  sleep(Math.random() * 3 + 1); // Sleep between 1-4 seconds
}

// Test teardown
export function teardown(data) {
  console.log('Completing load test');
  // You could perform teardown tasks here, such as cleaning up test data
}

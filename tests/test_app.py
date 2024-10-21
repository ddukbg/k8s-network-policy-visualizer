import unittest
from app import app, get_network_policies, get_pods, map_policies_to_pods

class TestK8sNetPolVisualizer(unittest.TestCase):

    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    def test_get_network_policies(self):
        policies = get_network_policies()
        self.assertIsNotNone(policies)
        self.assertIn('items', policies)

    def test_get_pods(self):
        pods = get_pods()
        self.assertIsNotNone(pods)
        self.assertIn('items', pods)

    def test_map_policies_to_pods(self):
        policies = get_network_policies()
        pods = get_pods()
        pod_map, edges = map_policies_to_pods(policies, pods)
        self.assertIsInstance(pod_map, dict)
        self.assertIsInstance(edges, list)

    def test_policy_details_endpoint(self):
        response = self.app.get('/policy/sample-policy')
        # 실제 환경에 맞게 assertions 추가
        # 예: self.assertEqual(response.status_code, 200)
        #     self.assertIn('ingress', response.get_json())

    def test_pod_details_endpoint(self):
        response = self.app.get('/pod/default/sample-pod')
        # 실제 환경에 맞게 assertions 추가
        # 예: self.assertEqual(response.status_code, 200)
        #     self.assertIn('labels', response.get_json())

if __name__ == '__main__':
    unittest.main()

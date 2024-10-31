#!/bin/bash

# 네임스페이스 생성
for i in {1..3}; do
  kubectl create namespace test-namespace-$i
done

# 디플로이먼트 생성
for ns in test-namespace-1 test-namespace-2 test-namespace-3; do
  for app in app-a app-b app-c; do
    kubectl create deployment $app --image=nginx:latest -n $ns
    kubectl scale deployment $app --replicas=2 -n $ns
    kubectl label pods -l app=$app app=$app -n $ns
  done
done

# 네트워크 정책 생성
kubectl apply -f networkpolicies.yaml

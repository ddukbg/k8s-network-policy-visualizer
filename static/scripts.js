// scripts.js

document.addEventListener('DOMContentLoaded', function() {
    const socket = io();

    // 로딩 오버레이 요소 가져오기
    const loadingOverlay = document.getElementById('loading-overlay');

    // 현재 선택된 리소스 타입 (기본값: deployment)
    let currentResourceType = 'deployment';

    // 노드 위치 저장을 위한 객체 (선택 사항)
    let nodePositions = {};

    // 초기 데이터 로드
    fetchData(currentResourceType);

    // 네임스페이스 리스트 로드
    fetch('/namespaces')
        .then(response => response.json())
        .then(data => {
            populateNamespaceFilters(data.namespaces);
        })
        .catch(error => {
            console.error('Error fetching namespaces:', error);
        });

    // 리소스 타입 필터 변경 시 데이터 로드
    document.getElementsByName('resource_type').forEach(function(radio) {
        radio.addEventListener('change', function() {
            if (this.checked) {
                currentResourceType = this.value;
                fetchData(currentResourceType);
            }
        });
    });

    // 그래프 초기화 함수
    function initializeGraph(data) {
        if (window.cy) {
            window.cy.destroy();
        }

        window.cy = cytoscape({
            container: document.getElementById('graph'),
            elements: data.nodes.concat(data.edges),
            style: [
                {
                    selector: 'node[group="deployment"]',
                    style: {
                        'background-color': '#2ECC40',
                        'label': 'data(label)',
                        'text-valign': 'center',
                        'color': '#fff',
                        'text-outline-width': 2,
                        'text-outline-color': '#2ECC40',
                        'font-size': '10px',
                        'width': 'label',
                        'height': 'label'
                    }
                },
                {
                    selector: 'node[group="pod"]',
                    style: {
                        'background-color': '#0074D9',
                        'label': 'data(label)',
                        'text-valign': 'center',
                        'color': '#fff',
                        'text-outline-width': 2,
                        'text-outline-color': '#0074D9',
                        'font-size': '10px',
                        'width': 'label',
                        'height': 'label'
                    }
                },
                {
                    selector: 'node[group="policy"]',
                    style: {
                        'background-color': '#FF4136',
                        'label': 'data(label)',
                        'text-valign': 'center',
                        'color': '#fff',
                        'text-outline-width': 2,
                        'text-outline-color': '#FF4136',
                        'font-size': '10px',
                        'width': 'label',
                        'height': 'label'
                    }
                },
                {
                    selector: 'node[group="ipblock"]',
                    style: {
                        'background-color': '#B10DC9',
                        'shape': 'rectangle',
                        'label': 'data(label)',
                        'text-valign': 'center',
                        'color': '#fff',
                        'text-outline-width': 2,
                        'text-outline-color': '#B10DC9',
                        'font-size': '10px',
                        'width': 'label',
                        'height': 'label'
                    }
                },
                {
                    selector: 'edge[type="ingress"]',
                    style: {
                        'width': 3,
                        'line-color': '#2ECC40',
                        'target-arrow-color': '#2ECC40',
                        'target-arrow-shape': 'triangle',
                        'curve-style': 'bezier',
                        'label': 'data(label)',
                        'font-size': '10px',
                        'text-rotation': 'autorotate'
                    }
                },
                {
                    selector: 'edge[type="egress"]',
                    style: {
                        'width': 3,
                        'line-color': '#FF851B',
                        'target-arrow-color': '#FF851B',
                        'target-arrow-shape': 'triangle',
                        'curve-style': 'bezier',
                        'label': 'data(label)',
                        'font-size': '10px',
                        'text-rotation': 'autorotate'
                    }
                },
                {
                    selector: 'edge[type="ingress-ipBlock"], edge[type="egress-ipBlock"]',
                    style: {
                        'width': 2,
                        'line-color': '#B10DC9',
                        'target-arrow-color': '#B10DC9',
                        'target-arrow-shape': 'diamond',
                        'curve-style': 'bezier',
                        'label': 'data(details.cidr)',
                        'font-size': '8px',
                        'text-rotation': 'autorotate',
                        'line-style': 'dashed'
                    }
                }
            ],
            layout: {
                name: 'cose',
                padding: 10,
                animate: false,
                nodeDimensionsIncludeLabels: true
            }
        });

        // 저장된 위치가 있으면 복원 (선택 사항)
        window.cy.nodes().forEach(function(node) {
            if(nodePositions[node.id()]) {
                node.position(nodePositions[node.id()]);
            }
        });

        // 노드 위치 변경 시 저장 (선택 사항)
        window.cy.on('dragfree', 'node', function(evt){
            var node = evt.target;
            nodePositions[node.id()] = node.position();
        });

        // 노드 클릭 시 상세 정보 표시
        cy.on('tap', 'node', function(evt){
            var node = evt.target;
            var content = '';

            if(node.data('group') === 'policy') {
                const policyName = node.data('label').split('/').pop(); // 네임스페이스/정책명 중 정책명 추출
                fetch(`/policy/${encodeURIComponent(policyName)}`)
                    .then(response => response.json())
                    .then(policyData => {
                        if(policyData.error) {
                            content = `<strong>Error:</strong> ${policyData.error}`;
                        } else {
                            content = `<strong>Policy:</strong> ${policyData.name}<br>`;
                            content += `<strong>Namespace:</strong> ${policyData.namespace}<br><br>`;
                            
                            // Ingress 규칙
                            if(policyData.ingress.length > 0) {
                                content += `<strong>Ingress Rules:</strong><br>`;
                                policyData.ingress.forEach((ingress, index) => {
                                    content += `<strong>Rule ${index + 1}:</strong><br>`;
                                    if(ingress.from) {
                                        content += `&nbsp;&nbsp;<strong>From:</strong> ${JSON.stringify(ingress.from)}<br>`;
                                    }
                                    if(ingress.ports) {
                                        const ports = ingress.ports.map(p => `${p.protocol}/${p.port}`).join(', ');
                                        content += `&nbsp;&nbsp;<strong>Ports:</strong> ${ports}<br>`;
                                    }
                                    if(ingress.ipBlock) {
                                        content += `&nbsp;&nbsp;<strong>IPBlock:</strong> ${JSON.stringify(ingress.ipBlock)}<br>`;
                                    }
                                    content += `<br>`;
                                });
                            } else {
                                content += `<strong>Ingress Rules:</strong> None<br>`;
                            }

                            // Egress 규칙
                            if(policyData.egress.length > 0) {
                                content += `<strong>Egress Rules:</strong><br>`;
                                policyData.egress.forEach((egress, index) => {
                                    content += `<strong>Rule ${index + 1}:</strong><br>`;
                                    if(egress.to) {
                                        content += `&nbsp;&nbsp;<strong>To:</strong> ${JSON.stringify(egress.to)}<br>`;
                                    }
                                    if(egress.ports) {
                                        const ports = egress.ports.map(p => `${p.protocol}/${p.port}`).join(', ');
                                        content += `&nbsp;&nbsp;<strong>Ports:</strong> ${ports}<br>`;
                                    }
                                    if(egress.ipBlock) {
                                        content += `&nbsp;&nbsp;<strong>IPBlock:</strong> ${JSON.stringify(egress.ipBlock)}<br>`;
                                    }
                                    content += `<br>`;
                                });
                            } else {
                                content += `<strong>Egress Rules:</strong> None<br>`;
                            }
                        }
                        document.getElementById('detail-content').innerHTML = content;
                    })
                    .catch(error => {
                        console.error('Error fetching policy details:', error);
                        content = `<strong>Error:</strong> Failed to fetch policy details.`;
                        document.getElementById('detail-content').innerHTML = content;
                    });
            } else if(node.data('group') === 'deployment') {
                const deploymentFullName = node.data('id'); // 네임스페이스/Deployment명 전체
                fetch(`/resource/deployment/${encodeURIComponent(deploymentFullName)}`)
                    .then(response => response.json())
                    .then(deploymentData => {
                        if(deploymentData.error) {
                            content = `<strong>Error:</strong> ${deploymentData.error}`;
                        } else {
                            content = `<strong>Deployment:</strong> ${deploymentData.name}<br>`;
                            content += `<strong>Namespace:</strong> ${deploymentData.namespace}<br>`;
                            content += `<strong>Labels:</strong> ${JSON.stringify(deploymentData.labels)}<br>`;
                            content += `<strong>Status:</strong> ${deploymentData.status}<br>`;
                        }
                        document.getElementById('detail-content').innerHTML = content;
                    })
                    .catch(error => {
                        console.error('Error fetching deployment details:', error);
                        content = `<strong>Error:</strong> Failed to fetch deployment details.`;
                        document.getElementById('detail-content').innerHTML = content;
                    });
            } else if(node.data('group') === 'pod') {
                const podFullName = node.data('id'); // 네임스페이스/Pod명 전체
                fetch(`/resource/pod/${encodeURIComponent(podFullName)}`)
                    .then(response => response.json())
                    .then(podData => {
                        if(podData.error) {
                            content = `<strong>Error:</strong> ${podData.error}`;
                        } else {
                            content = `<strong>Pod:</strong> ${podData.name}<br>`;
                            content += `<strong>Namespace:</strong> ${podData.namespace}<br>`;
                            content += `<strong>Labels:</strong> ${JSON.stringify(podData.labels)}<br>`;
                            content += `<strong>Status:</strong> ${podData.status}<br>`;
                        }
                        document.getElementById('detail-content').innerHTML = content;
                    })
                    .catch(error => {
                        console.error('Error fetching pod details:', error);
                        content = `<strong>Error:</strong> Failed to fetch pod details.`;
                        document.getElementById('detail-content').innerHTML = content;
                    });
            } else if(node.data('group') === 'ipblock') {
                // IPBlock 상세 정보 처리
                const ipBlockLabel = node.data('label');
                content = `<strong>IPBlock:</strong> ${ipBlockLabel}<br>`;
                document.getElementById('detail-content').innerHTML = content;
            }
        });

    }

    // 네임스페이스 체크박스 생성 함수
    function populateNamespaceFilters(namespaces) {
        const filtersDiv = document.getElementById('namespace-filters');
        
        // ALL 체크박스 추가
        const allLabel = document.createElement('label');
        const allCheckbox = document.createElement('input');
        allCheckbox.type = 'checkbox';
        allCheckbox.id = 'filter-all';
        allCheckbox.checked = true;
        allCheckbox.addEventListener('change', handleAllCheckboxChange);
        allLabel.appendChild(allCheckbox);
        allLabel.appendChild(document.createTextNode('ALL'));
        filtersDiv.appendChild(allLabel);
        
        // 네임스페이스별 체크박스 추가
        namespaces.forEach(namespace => {
            const label = document.createElement('label');
            const checkbox = document.createElement('input');
            checkbox.type = 'checkbox';
            checkbox.className = 'namespace-checkbox';
            checkbox.value = namespace;
            checkbox.checked = true;
            checkbox.addEventListener('change', handleNamespaceCheckboxChange);
            label.appendChild(checkbox);
            label.appendChild(document.createTextNode(namespace));
            filtersDiv.appendChild(label);
        });
    }

    // ALL 체크박스 변경 핸들러
    function handleAllCheckboxChange(e) {
        const allCheckbox = document.getElementById('filter-all');
        const namespaceCheckboxes = document.querySelectorAll('.namespace-checkbox');

        if (allCheckbox.checked) {
            namespaceCheckboxes.forEach(cb => cb.checked = true);
        } else {
            namespaceCheckboxes.forEach(cb => cb.checked = false);
        }

        filterGraph();
    }

    // 네임스페이스 체크박스 변경 핸들러
    function handleNamespaceCheckboxChange(e) {
        const allCheckbox = document.getElementById('filter-all');
        const namespaceCheckboxes = document.querySelectorAll('.namespace-checkbox');
        const total = namespaceCheckboxes.length;
        const checked = document.querySelectorAll('.namespace-checkbox:checked').length;

        if (checked === 0) {
            allCheckbox.checked = false;
        } else if (checked === total) {
            allCheckbox.checked = true;
        } else {
            allCheckbox.checked = false;
        }

        filterGraph();
    }

    // 그래프 필터링 함수
    function filterGraph() {
        const allCheckbox = document.getElementById('filter-all');
        const namespaceCheckboxes = document.querySelectorAll('.namespace-checkbox');
        const selectedNamespaces = [];

        if (allCheckbox.checked) {
            namespaceCheckboxes.forEach(cb => cb.checked = true);
            selectedNamespaces.push(...Array.from(namespaceCheckboxes).map(cb => cb.value));
        } else {
            namespaceCheckboxes.forEach(cb => {
                if(cb.checked) {
                    selectedNamespaces.push(cb.value);
                }
            });
        }

        window.cy.nodes().forEach(function(node) {
            const nodeId = node.data('id');
            const namespace = nodeId.split('/')[0];
            if(selectedNamespaces.includes(namespace)) {
                node.show();
            } else {
                node.hide();
            }
        });

        window.cy.edges().forEach(function(edge) {
            const sourceVisible = edge.source().visible();
            const targetVisible = edge.target().visible();
            if(sourceVisible && targetVisible) {
                edge.show();
            } else {
                edge.hide();
            }
        });
    }

    // 실시간 업데이트 수신 및 그래프 업데이트
    socket.on('update_deployment', function(graphData) {
        if (currentResourceType === 'deployment') {
            showLoading(); // 로딩 시작
            cy.batch(function() {
                cy.elements().remove();
                cy.add(graphData.nodes.concat(graphData.edges));
                cy.layout({
                    name: 'cose',
                    padding: 10,
                    animate: false,
                    nodeDimensionsIncludeLabels: true
                }).run();
                filterGraph(); // 필터 재적용
                hideLoading(); // 로딩 완료
            });
        }
    });

    socket.on('update_pod', function(graphData) {
        if (currentResourceType === 'pod') {
            showLoading(); // 로딩 시작
            cy.batch(function() {
                cy.elements().remove();
                cy.add(graphData.nodes.concat(graphData.edges));
                cy.layout({
                    name: 'cose',
                    padding: 10,
                    animate: false,
                    nodeDimensionsIncludeLabels: true
                }).run();
                filterGraph(); // 필터 재적용
                hideLoading(); // 로딩 완료
            });
        }
    });

    // 데이터 가져오는 함수
    function fetchData(resource_type) {
        showLoading(); // 로딩 시작
        fetch(`/data?resource_type=${resource_type}`)
            .then(response => response.json())
            .then(data => {
                initializeGraph(data);
                hideLoading(); // 로딩 완료
            })
            .catch(error => {
                console.error('Error fetching data:', error);
                hideLoading(); // 로딩 완료
            });
    }

    // 로딩 오버레이 표시 함수
    function showLoading() {
        loadingOverlay.style.display = 'flex';
    }

    // 로딩 오버레이 숨김 함수
    function hideLoading() {
        loadingOverlay.style.display = 'none';
    }

    // 현재 필터 상태 재적용 함수 (선택 사항)
    function applyCurrentFilters() {
        const allCheckbox = document.getElementById('filter-all');
        const namespaceCheckboxes = document.querySelectorAll('.namespace-checkbox');
        const selectedNamespaces = [];

        if (allCheckbox.checked) {
            namespaceCheckboxes.forEach(cb => cb.checked = true);
            selectedNamespaces.push(...Array.from(namespaceCheckboxes).map(cb => cb.value));
        } else {
            namespaceCheckboxes.forEach(cb => {
                if(cb.checked) {
                    selectedNamespaces.push(cb.value);
                }
            });
        }

        window.cy.nodes().forEach(function(node) {
            const nodeId = node.data('id');
            const namespace = nodeId.split('/')[0];
            if(selectedNamespaces.includes(namespace)) {
                node.show();
            } else {
                node.hide();
            }
        });

        window.cy.edges().forEach(function(edge) {
            const sourceVisible = edge.source().visible();
            const targetVisible = edge.target().visible();
            if(sourceVisible && targetVisible) {
                edge.show();
            } else {
                edge.hide();
            }
        });
    }

    // 검색 기능 구현
    document.getElementById('search').addEventListener('input', function(e) {
        var query = e.target.value.toLowerCase();
        window.cy.nodes().forEach(function(node) {
            var label = node.data('label').toLowerCase();
            if(label.includes(query)) {
                node.show();
            } else {
                node.hide();
            }
        });
        window.cy.edges().forEach(function(edge) {
            var sourceVisible = edge.source().visible();
            var targetVisible = edge.target().visible();
            if(sourceVisible && targetVisible) {
                edge.show();
            } else {
                edge.hide();
            }
        });
    });
});

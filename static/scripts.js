document.addEventListener('DOMContentLoaded', function() {
    const socket = io();

    // 초기 데이터 로드
    fetch('/data')
        .then(response => response.json())
        .then(data => {
            initializeGraph(data);
        })
        .catch(error => {
            console.error('Error fetching data:', error);
        });

    // 네임스페이스 리스트 로드
    fetch('/namespaces')
        .then(response => response.json())
        .then(data => {
            populateNamespaceFilters(data.namespaces);
        })
        .catch(error => {
            console.error('Error fetching namespaces:', error);
        });

    // 그래프 초기화 함수
    function initializeGraph(data) {
        window.cy = cytoscape({
            container: document.getElementById('graph'),
            elements: data.nodes.concat(data.edges),
            style: [
                {
                    selector: 'node[group="pod"]',
                    style: {
                        'background-color': '#0074D9',
                        'label': 'data(label)',
                        'text-valign': 'center',
                        'color': '#fff',
                        'text-outline-width': 2,
                        'text-outline-color': '#0074D9'
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
                        'text-outline-color': '#FF4136'
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
                }
            ],
            layout: {
                name: 'cose',
                padding: 10
            }
        });

        // 노드 클릭 시 상세 정보 표시
        // scripts.js 내 노드 클릭 핸들러 수정
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
            } else if(node.data('group') === 'pod') {
                const podName = node.data('label'); // 네임스페이스/Pod명 전체
                fetch(`/pod/${encodeURIComponent(podName)}`)
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
    socket.on('update', function(data) {
        if (window.cy) {
            // 기존 그래프 삭제
            window.cy.elements().remove();

            // 새로운 데이터 추가
            window.cy.add(data.nodes.concat(data.edges));

            // 레이아웃 재적용
            window.cy.layout({ name: 'cose', padding: 10 }).run();

            // 현재 필터 적용
            applyCurrentFilters();
        }
    });

    // 현재 필터 상태 재적용 함수
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

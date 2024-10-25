document.addEventListener('DOMContentLoaded', function() {
    // 전역 변수 선언
    const socket = io();
    const loadingOverlay = document.getElementById('loading-overlay');
    let currentResourceType = 'deployment';
    let currentFilters = new Set();
    let currentAnalysisMode = 'auto';
    let communicationData = null;
    window.cy = null;

    // 초기화
    initializeApp();

    function initializeApp() {
        // 네임스페이스 로드
        loadNamespaces();
        // 초기 데이터 로드
        fetchData(currentResourceType);
        // 이벤트 리스너 설정
        setupEventListeners();
    }

    function setupEventListeners() {
        // 리소스 타입 변경 리스너
        document.getElementsByName('resource_type').forEach(function(radio) {
            radio.addEventListener('change', function() {
                if (this.checked) {
                    currentResourceType = this.value;
                    fetchData(currentResourceType);
                }
            });
        });
        
        // 그래프 컨트롤 설정 추가
        setupGraphControls();

        // 분석 모드 변경 이벤트
        document.getElementsByName('analysis-mode').forEach(radio => {
            radio.addEventListener('change', function(e) {
                currentAnalysisMode = e.target.value;
                const pathAnalyzer = document.querySelector('.path-analyzer');
                pathAnalyzer.style.display = currentAnalysisMode === 'path' ? 'block' : 'none';
                
                if (currentAnalysisMode === 'auto') {
                    resetCommunicationHighlights();
                }
            });
        });
        // 리소스 선택 이벤트
        document.getElementById('source-selector').addEventListener('change', updatePathAnalysis);
        document.getElementById('target-selector').addEventListener('change', updatePathAnalysis);
        
        // 경로 분석 버튼 클릭 이벤트
        document.getElementById('analyze-path').addEventListener('click', analyzeCommunicationPath);

        // 네임스페이스 필터 체크박스 이벤트
        document.querySelectorAll('.namespace-checkbox').forEach(checkbox => {
            checkbox.addEventListener('change', filterGraph);
        });

        // ALL 체크박스 이벤트
        const allCheckbox = document.getElementById('filter-all');
        if (allCheckbox) {
            allCheckbox.addEventListener('change', function(e) {
                document.querySelectorAll('.namespace-checkbox').forEach(cb => {
                    cb.checked = e.target.checked;
                });
                filterGraph();
            });
        }
    }

    // 초기화 시 이벤트 리스너 설정 호출
    setupEventListeners();

    // 통신 분석 관련 함수들 추가
    function updateResourceSelectors() {
        const sourceSelector = document.getElementById('source-selector');
        const targetSelector = document.getElementById('target-selector');
        
        if (!sourceSelector || !targetSelector || !window.cy) {
            console.log('Selectors or cy not ready');
            return;
        }
        
        console.log('Updating resource selectors. Current graph state:', {
            totalNodes: window.cy.nodes().length,
            visibleNodes: window.cy.nodes(':visible').length
        });
        
        // 현재 보이는 노드만 선택 가능하도록 수정
        const visibleNodes = window.cy.nodes(':visible').filter(node => 
            node.data('group') === 'pod' || node.data('group') === 'deployment'
        );
        
        console.log('Filtered visible nodes:', visibleNodes.map(node => ({
            id: node.data('id'),
            label: node.data('label'),
            group: node.data('group')
        })));
        
        // 셀렉터 옵션 업데이트
        const options = ['<option value="">Select Resource</option>'];
        visibleNodes.forEach(node => {
            options.push(`<option value="${node.data('id')}">${node.data('label')} (${node.data('group')})</option>`);
        });
        
        sourceSelector.innerHTML = options.join('');
        targetSelector.innerHTML = options.join('');
    }

    function updatePathAnalysis() {
        const source = document.getElementById('source-selector').value;
        const target = document.getElementById('target-selector').value;
        
        if (source && target) {
            document.getElementById('analyze-path').disabled = false;
        } else {
            document.getElementById('analyze-path').disabled = true;
        }
    }

    function analyzeCommunicationPath() {
        const source = document.getElementById('source-selector').value;
        const target = document.getElementById('target-selector').value;
        
        if (!source || !target) return;
        
        showLoading();
        fetch(`/check-communication?source=${encodeURIComponent(source)}&target=${encodeURIComponent(target)}&resource_type=${currentResourceType}`)
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    console.error('Analysis error:', data.error);
                    // 에러 메시지 표시
                    document.querySelector('.status-text').textContent = data.error;
                    return;
                }
                displayCommunicationResults(data, source, target);
                highlightCommunicationPath(data, source, target);
            })
            .catch(error => {
                console.error('Error analyzing communication:', error);
                document.querySelector('.status-text').textContent = 'Error analyzing communication path';
            })
            .finally(() => {
                hideLoading();
            });
    }

    function displayCommunicationResults(data, source, target) {
        const statusIndicator = document.querySelector('.status-indicator');
        const statusText = document.querySelector('.status-text');
        const policiesList = document.getElementById('affected-policies');
        const portsList = document.getElementById('allowed-ports');
        
        // 상태 표시 업데이트
        statusIndicator.className = 'status-indicator ' + (data.allowed ? 'allowed' : 'blocked');
        statusText.textContent = data.allowed ? 'Communication allowed' : 'Communication blocked';
        
        // 정책 목록 업데이트
        policiesList.innerHTML = '';
        const policies = [...new Set([...data.ingress_policies, ...data.egress_policies])];
        if (policies.length > 0) {
            policies.forEach(policy => {
                const li = document.createElement('li');
                li.textContent = policy;
                policiesList.appendChild(li);
            });
        } else {
            const li = document.createElement('li');
            li.textContent = 'No affected policies';
            policiesList.appendChild(li);
        }
        
        // 포트 목록 업데이트
        portsList.innerHTML = '';
        if (data.ports && data.ports.length > 0) {
            data.ports.forEach(port => {
                const li = document.createElement('li');
                li.textContent = port;
                portsList.appendChild(li);
            });
        } else {
            const li = document.createElement('li');
            li.textContent = 'All ports';
            portsList.appendChild(li);
        }
    }

    function highlightCommunicationPath(data, source, target) {
        resetCommunicationHighlights();
        
        console.log('Graph nodes:', window.cy.nodes().map(n => ({
            id: n.id(),
            data_id: n.data('id'),
            label: n.data('label')
        })));
        console.log('Looking for nodes:', source, target);
    
        // 노드 찾기 방식 수정
        const sourceNode = window.cy.nodes().find(node => node.data('id') === source);
        const targetNode = window.cy.nodes().find(node => node.data('id') === target);
        
        if (!sourceNode || !targetNode) {
            console.error('Missing nodes:', {
                sourceFound: !!sourceNode,
                targetFound: !!targetNode,
                availableNodes: window.cy.nodes().map(n => n.data('id'))
            });
            document.querySelector('.status-text').textContent = 
                'Error: Selected resources not found in current view. Try changing filters.';
            return;
        }
    
        // 노드 하이라이트
        sourceNode.addClass('highlighted');
        targetNode.addClass('highlighted');
        
        try {
            // 엣지 ID를 고유하게 생성
            const edgeId = `communication-edge-${Date.now()}`;
            
            // 통신 가능성에 따른 엣지 스타일 적용
            if (data.allowed) {
                const portLabel = Array.isArray(data.ports) ? data.ports.join(', ') : 'all ports';
                window.cy.add({
                    group: 'edges',
                    data: {
                        id: edgeId,
                        source: sourceNode.data('id'),  // data('id') 사용
                        target: targetNode.data('id'),  // data('id') 사용
                        connectionType: 'allowed',
                        label: portLabel
                    }
                }).addClass('communication-path');
            } else {
                window.cy.add({
                    group: 'edges',
                    data: {
                        id: edgeId,
                        source: sourceNode.data('id'),  // data('id') 사용
                        target: targetNode.data('id'),  // data('id') 사용
                        connectionType: 'blocked',
                        label: 'Blocked'
                    }
                }).addClass('blocked-path');
            }
    
            // 하이라이트된 요소들이 보이도록 뷰 조정
            const elementsToShow = window.cy.elements('.highlighted, .communication-path, .blocked-path');
            if (elementsToShow.length > 0) {
                window.cy.fit(elementsToShow, 50);
            }
    
        } catch (error) {
            console.error('Error highlighting path:', error);
            console.error('Source node:', sourceNode?.data());
            console.error('Target node:', targetNode?.data());
            document.querySelector('.status-text').textContent = 
                'Error highlighting communication path: ' + error.message;
        }
    }
    

    function resetCommunicationHighlights() {
        window.cy.elements('.highlighted, .communication-path, .blocked-path').removeClass('highlighted communication-path blocked-path');
        window.cy.elements().remove('[connectionType]');
    }

    function filterGraph() {
        if (!window.cy) return;
    
        const selectedNamespaces = Array.from(document.querySelectorAll('.namespace-checkbox:checked'))
            .map(cb => cb.value);
    
        window.cy.batch(() => {
            window.cy.nodes().forEach(node => {
                const namespace = node.data('id').split('/')[0];
                if (selectedNamespaces.includes(namespace)) {
                    node.show();
                } else {
                    node.hide();
                }
            });
    
            window.cy.edges().forEach(edge => {
                const sourceVisible = edge.source().visible();
                const targetVisible = edge.target().visible();
                if (sourceVisible && targetVisible) {
                    edge.show();
                } else {
                    edge.hide();
                }
            });
        });
    
        // 필터 적용 후 리소스 셀렉터 업데이트
        updateResourceSelectors();
    }


    function loadNamespaces() {
        fetch('/namespaces')
            .then(response => response.json())
            .then(data => {
                setupNamespaceFilters(data.namespaces);
                currentFilters = new Set(data.namespaces);
            })
            .catch(error => {
                console.error('Error fetching namespaces:', error);
            });
    }

    function setupNamespaceFilters(namespaces) {
        const filtersDiv = document.getElementById('namespace-filters');
        filtersDiv.innerHTML = ''; // 기존 필터 초기화

        // ALL 체크박스 추가
        const allLabel = createCheckboxLabel('filter-all', 'ALL', true);
        allLabel.querySelector('input').addEventListener('change', handleAllCheckboxChange);
        filtersDiv.appendChild(allLabel);

        // 개별 네임스페이스 체크박스 추가
        namespaces.forEach(namespace => {
            const label = createCheckboxLabel(`ns-${namespace}`, namespace, true, 'namespace-checkbox');
            label.querySelector('input').addEventListener('change', handleNamespaceCheckboxChange);
            filtersDiv.appendChild(label);
        });
    }

    function setupGraphControls() {
        // 레이아웃 변경 처리
        document.getElementById('layout-select').addEventListener('change', function(e) {
            applyLayout(e.target.value);
        });
    
        // 줌 컨트롤
        document.getElementById('zoom-in').addEventListener('click', () => {
            window.cy.zoom(window.cy.zoom() * 1.2);
        });
    
        document.getElementById('zoom-out').addEventListener('click', () => {
            window.cy.zoom(window.cy.zoom() / 1.2);
        });
    
        document.getElementById('zoom-fit').addEventListener('click', () => {
            window.cy.fit();
        });
    
        // 네임스페이스 그룹핑
        document.getElementById('group-by-namespace').addEventListener('change', function(e) {
            if (e.target.checked) {
                applyNamespaceGrouping();
            } else {
                removeNamespaceGrouping();
            }
        });
    
        // 레이아웃 저장
        document.getElementById('save-layout').addEventListener('click', saveCurrentLayout);
    }
    
    function applyLayout(layoutName) {
        const layoutConfig = {
            grid: {
                name: 'grid',
                padding: 30,
                spacingFactor: 1.5
            },
            circle: {
                name: 'circle',
                padding: 30,
                spacingFactor: 1.5
            },
            concentric: {
                name: 'concentric',
                padding: 30,
                minNodeSpacing: 50,
                concentric: function(node) {
                    return node.data('group') === 'policy' ? 2 : 1;
                }
            },
            breadthfirst: {
                name: 'breadthfirst',
                padding: 30,
                spacingFactor: 1.5,
                directed: true
            }
        };
    
        window.cy.layout(layoutConfig[layoutName]).run();
    }
    
    function applyNamespaceGrouping() {
        // 네임스페이스별로 노드 위치 조정
        const namespaces = new Set();
        window.cy.nodes().forEach(node => {
            const namespace = node.data('id').split('/')[0];
            namespaces.add(namespace);
        });
    
        const namespaceArray = Array.from(namespaces);
        const angleStep = (2 * Math.PI) / namespaceArray.length;
        const radius = 300;
    
        namespaceArray.forEach((namespace, i) => {
            const angle = i * angleStep;
            const x = radius * Math.cos(angle);
            const y = radius * Math.sin(angle);
            
            window.cy.nodes().filter(node => 
                node.data('id').startsWith(namespace + '/')
            ).forEach((node, j, nodes) => {
                const innerRadius = radius / 2;
                const innerAngle = (j / nodes.length) * 2 * Math.PI;
                node.position({
                    x: x + innerRadius * Math.cos(innerAngle),
                    y: y + innerRadius * Math.sin(innerAngle)
                });
            });
        });
    }
    
    function removeNamespaceGrouping() {
        // 기본 레이아웃으로 복귀
        applyLayout(document.getElementById('layout-select').value);
    }
    
    function saveCurrentLayout() {
        const positions = {};
        window.cy.nodes().forEach(node => {
            positions[node.id()] = node.position();
        });
        localStorage.setItem('savedLayout', JSON.stringify(positions));
        alert('Layout saved!');
    }
    
    function restoreLayout() {
        const savedLayout = localStorage.getItem('savedLayout');
        if (savedLayout) {
            const positions = JSON.parse(savedLayout);
            window.cy.nodes().forEach(node => {
                if (positions[node.id()]) {
                    node.position(positions[node.id()]);
                }
            });
        }
    }
    
    function createCheckboxLabel(id, text, checked, className = '') {
        const label = document.createElement('label');
        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.id = id;
        checkbox.value = text;
        checkbox.checked = checked;
        if (className) checkbox.className = className;
        label.appendChild(checkbox);
        label.appendChild(document.createTextNode(text));
        return label;
    }

    function handleAllCheckboxChange(e) {
        const isChecked = e.target.checked;
        document.querySelectorAll('.namespace-checkbox').forEach(cb => {
            cb.checked = isChecked;
            if (isChecked) {
                currentFilters.add(cb.value);
            } else {
                currentFilters.delete(cb.value);
            }
        });
        applyFilters();
    }

    function handleNamespaceCheckboxChange(e) {
        const checkbox = e.target;
        if (checkbox.checked) {
            currentFilters.add(checkbox.value);
        } else {
            currentFilters.delete(checkbox.value);
        }

        const allCheckbox = document.getElementById('filter-all');
        const namespaceCheckboxes = document.querySelectorAll('.namespace-checkbox');
        allCheckbox.checked = 
            Array.from(namespaceCheckboxes).every(cb => cb.checked);
        
        applyFilters();
    }

    function applyFilters() {
        if (!window.cy) return;

        window.cy.batch(() => {
            window.cy.nodes().forEach(node => {
                const namespace = node.data('id').split('/')[0];
                if (currentFilters.has(namespace)) {
                    node.show();
                } else {
                    node.hide();
                }
            });

            window.cy.edges().forEach(edge => {
                const sourceVisible = edge.source().visible();
                const targetVisible = edge.target().visible();
                if (sourceVisible && targetVisible) {
                    edge.show();
                } else {
                    edge.hide();
                }
            });
        });
    }

    function fetchData(resource_type) {
        showLoading();
        console.log('Fetching data for resource type:', resource_type);
        
        fetch(`/data?resource_type=${resource_type}`)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                console.log('Received data:', {
                    nodeCount: data.nodes?.length || 0,
                    nodes: data.nodes,
                    edgeCount: data.edges?.length || 0,
                    edges: data.edges
                });
                if (!data.nodes || !data.edges) {
                    throw new Error('Invalid data structure received');
                }
                initializeGraph(data);
                applyFilters();
                updateResourceSelectors();
                hideLoading();
            })
            .catch(error => {
                console.error('Error fetching data:', error);
                document.querySelector('.status-text').textContent = 
                    'Error loading graph data: ' + error.message;
                hideLoading();
            });
    }

    function initializeGraph(data) {
        console.log('Raw data received:', data);  // 원본 데이터 확인
    
        if (window.cy) {
            window.cy.destroy();
            console.log('Previous cy instance destroyed');
        }
    
        // 데이터 구조 확인
        if (!Array.isArray(data.nodes) || !Array.isArray(data.edges)) {
            console.error('Invalid data structure:', data);
            return;
        }
    
        // 유효한 엣지 필터링
        const validEdges = data.edges.filter(edge => {
            const sourceExists = data.nodes.some(node => node.data.id === edge.data.source);
            const targetExists = data.nodes.some(node => node.data.id === edge.data.target);
            console.log('Edge validation:', {
                edge: edge,
                sourceExists,
                targetExists
            });
            return sourceExists && targetExists;
        });
    
        // Cytoscape 요소 형식 확인
        const elements = {
            nodes: data.nodes.map(node => ({
                data: {
                    id: node.data.id,
                    label: node.data.label,
                    group: node.data.group
                }
            })),
            edges: validEdges.map(edge => ({
                data: {
                    id: `edge-${edge.data.source}-${edge.data.target}`,
                    source: edge.data.source,
                    target: edge.data.target,
                    type: edge.data.type,
                    label: edge.data.label
                }
            }))
        };
    
        console.log('Formatted elements:', elements);
    
        try {
            window.cy = cytoscape({
                container: document.getElementById('graph'),
                elements: elements,
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
                            'width': '30px',
                            'height': '30px'
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
                            'width': '30px',
                            'height': '30px'
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
                            'font-size': '12px',
                            'width': '40px',
                            'height': '40px',
                            'border-width': '3px',
                            'border-color': '#D50000'
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
                            'font-size': '8px',
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
                            'font-size': '8px',
                            'text-rotation': 'autorotate'
                        }
                    }
                ],
                layout: {
                    name: 'grid',
                    padding: 30,
                    spacingFactor: 1.5
                }
            });
    
            console.log('Cytoscape instance created with nodes:', window.cy.nodes().length);
            
            // 노드가 제대로 추가되었는지 확인
            window.cy.nodes().forEach(node => {
                console.log('Node in graph:', {
                    id: node.id(),
                    data: node.data()
                });
            });
    
            // 이벤트 핸들러 설정
            window.cy.on('tap', 'node', function(evt) {
                handleNodeClick(evt.target);
            });
    
        } catch (error) {
            console.error('Error creating cytoscape instance:', error);
        }
    
        updateResourceSelectors();
    }

    // handleNodeClick 함수 추가
    function handleNodeClick(node) {
        console.log('Clicked node:', {
            id: node.id(),
            data_id: node.data('id'),
            group: node.data('group')
        });

        const nodeData = node.data();
        let endpoint = '';
        
        if (nodeData.group === 'policy') {
            endpoint = `/policy/${encodeURIComponent(nodeData.label)}`;
        } else {
            endpoint = `/resource/${nodeData.group}/${encodeURIComponent(nodeData.id)}`;
        }

        if (endpoint) {
            fetch(endpoint)
                .then(response => response.json())
                .then(data => displayNodeDetails(data, nodeData.group))
                .catch(error => console.error('Error fetching node details:', error));
        }
    }

    function setupNodeClickHandler() {
        window.cy.on('tap', 'node', function(evt) {
            const node = evt.target;
            const nodeData = node.data();
            let endpoint = '';
            
            if (nodeData.group === 'policy') {
                endpoint = `/policy/${encodeURIComponent(nodeData.label)}`;
            } else {
                endpoint = `/resource/${nodeData.group}/${encodeURIComponent(nodeData.id)}`;
            }

            if (endpoint) {
                fetch(endpoint)
                    .then(response => response.json())
                    .then(data => displayNodeDetails(data, nodeData.group))
                    .catch(error => console.error('Error fetching node details:', error));
            }
        });
    }

    function displayNodeDetails(data, type) {
        const detailContent = document.getElementById('detail-content');
        let content = '';

        if (type === 'policy') {
            content = createPolicyDetails(data);
        } else {
            content = createResourceDetails(data, type);
        }

        detailContent.innerHTML = content;
    }

    function showLoading() {
        loadingOverlay.style.display = 'flex';
    }

    function hideLoading() {
        loadingOverlay.style.display = 'none';
    }

    // 실시간 업데이트 처리
    socket.on(`update_${currentResourceType}`, function(graphData) {
        initializeGraph(graphData);
        applyFilters();
    });
});

// 헬퍼 함수들
function createPolicyDetails(data) {
    return `
        <h3>Network Policy: ${data.name}</h3>
        <p><strong>Namespace:</strong> ${data.namespace}</p>
        <div class="rules">
            <h4>Ingress Rules:</h4>
            ${formatRules(data.ingress)}
            <h4>Egress Rules:</h4>
            ${formatRules(data.egress)}
        </div>
    `;
}

function createResourceDetails(data, type) {
    let content = `
        <h3>${type.charAt(0).toUpperCase() + type.slice(1)}: ${data.name}</h3>
        <p><strong>Namespace:</strong> ${data.namespace}</p>
        <p><strong>Status:</strong> ${data.status}</p>
        <p><strong>Labels:</strong></p>
        <pre>${JSON.stringify(data.labels, null, 2)}</pre>
    `;

    if (type === 'pod') {
        content += `
            <p><strong>Node:</strong> ${data.node}</p>
            <p><strong>IP:</strong> ${data.ip}</p>
            <h4>Containers:</h4>
            <ul>
                ${data.containers.map(container => `
                    <li>
                        ${container.name} (${container.image})
                        <br>Ready: ${container.ready ? '✅' : '❌'}
                    </li>
                `).join('')}
            </ul>
        `;
    }

    return content;
}

function formatRules(rules) {
    if (!rules || rules.length === 0) {
        return '<p>No rules defined</p>';
    }

    return rules.map((rule, index) => `
        <div class="rule">
            <p><strong>Rule ${index + 1}:</strong></p>
            ${formatPorts(rule.ports)}
            ${formatSelectors(rule.from || rule.to)}
        </div>
    `).join('');
}

function formatPorts(ports) {
    if (!ports || ports.length === 0) {
        return '<p>All ports</p>';
    }

    return `
        <p><strong>Ports:</strong></p>
        <ul>
            ${ports.map(port => `
                <li>${port.protocol || 'TCP'}/${port.port}</li>
            `).join('')}
        </ul>
    `;
}

function formatSelectors(selectors) {
    if (!selectors || selectors.length === 0) {
        return '<p>No selectors defined</p>';
    }

    return `
        <p><strong>Selectors:</strong></p>
        <ul>
            ${selectors.map(selector => `
                <li>${formatSelector(selector)}</li>
            `).join('')}
        </ul>
    `;
}

function formatSelector(selector) {
    if (selector.podSelector && Object.keys(selector.podSelector).length > 0) {
        return `Pod Selector: ${JSON.stringify(selector.podSelector)}`;
    }
    if (selector.namespaceSelector && Object.keys(selector.namespaceSelector).length > 0) {
        return `Namespace Selector: ${JSON.stringify(selector.namespaceSelector)}`;
    }
    if (selector.ipBlock) {
        return `IP Block: ${selector.ipBlock.cidr}${
            selector.ipBlock.except ? ` (except: ${selector.ipBlock.except.join(', ')})` : ''
        }`;
    }
    return 'Empty selector';
}
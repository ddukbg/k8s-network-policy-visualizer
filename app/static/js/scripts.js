document.addEventListener('DOMContentLoaded', function() {
    // 전역 변수 선언
    const socket = io();
    const loadingOverlay = document.getElementById('loading-overlay');
    let currentResourceType = 'deployment';
    let currentFilters = new Set();
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
    }
    
    // 초기화 시 이벤트 리스너 설정 호출
    setupEventListeners();

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

    function fetchData(resourceType) {
        showLoading();
        fetch(`/data?resource_type=${resourceType}`)
            .then(response => response.json())
            .then(data => {
                initializeGraph(data);
                applyFilters();
                hideLoading();
            })
            .catch(error => {
                console.error('Error fetching data:', error);
                hideLoading();
            });
    }

    function initializeGraph(data) {
        if (window.cy) {
            window.cy.destroy();
        }
    
        const validEdges = data.edges.filter(edge => {
            const sourceExists = data.nodes.some(node => node.data.id === edge.data.source);
            const targetExists = data.nodes.some(node => node.data.id === edge.data.target);
            return sourceExists && targetExists;
        });
    
        window.cy = cytoscape({
            container: document.getElementById('graph'),
            elements: {
                nodes: data.nodes,
                edges: validEdges
            },
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
        
        if (localStorage.getItem('savedLayout')) {
            restoreLayout();
        }

        setupNodeClickHandler();
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
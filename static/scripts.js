/**
 * Kubernetes Network Policy Visualizer 2.0
 * 현대적인 JavaScript ES6+ 기반 클라이언트 사이드 코드
 */

class NetworkPolicyVisualizer {
    constructor() {
        this.cy = null;
        this.socket = null;
        this.currentData = null;
        this.searchTimeout = null;
        this.isLoading = false;
        
        // UI 요소 참조
        this.elements = {
            graph: document.getElementById('graph'),
            search: document.getElementById('search'),
            searchClear: document.getElementById('search-clear'),
            namespaceFilters: document.getElementById('namespace-filters'),
            detailsPanel: document.getElementById('details-panel'),
            detailsContent: document.getElementById('details-content'),
            closeDetails: document.getElementById('close-details'),
            loadingOverlay: document.getElementById('loading-overlay'),
            connectionStatus: document.getElementById('connection-status'),
            connectionText: document.getElementById('connection-text'),
            
            // 통계 카운터
            policyCount: document.getElementById('policy-count'),
            resourceCount: document.getElementById('resource-count'),
            edgeCount: document.getElementById('edge-count'),
            namespaceCount: document.getElementById('namespace-count'),
            
            // 버튼들
            refreshBtn: document.getElementById('refresh-btn'),
            fitBtn: document.getElementById('fit-btn'),
            layoutBtn: document.getElementById('layout-btn'),
            exportBtn: document.getElementById('export-btn'),
            
            // 라디오 버튼
            resourceTypeRadios: document.querySelectorAll('input[name="resource_type"]')
        };
        
        this.layouts = ['cose-bilkent', 'cose', 'circle', 'grid'];
        this.currentLayoutIndex = 0;
        
        this.init();
    }
    
    async init() {
        try {
            console.log('애플리케이션 초기화 시작');
            this.showLoading('초기화 중...');
            
            console.log('이벤트 리스너 설정 중...');
            this.setupEventListeners();
            
            console.log('Socket.IO 설정 중...');
            this.setupSocket();
            
            console.log('Cytoscape 초기화 중...');
            this.initCytoscape();
            
            console.log('초기 데이터 로딩 중...');
            await this.loadInitialData();
            
            console.log('초기화 완료');
            this.showToast('애플리케이션이 성공적으로 초기화되었습니다.', 'success');
        } catch (error) {
            console.error('초기화 실패:', error);
            this.showToast('초기화에 실패했습니다: ' + error.message, 'error');
            // 초기화 실패시에도 로딩을 숨김
            this.hideLoading();
        }
    }
    
    setupEventListeners() {
        // 검색 기능
        this.elements.search.addEventListener('input', (e) => {
            clearTimeout(this.searchTimeout);
            this.searchTimeout = setTimeout(() => {
                this.handleSearch(e.target.value);
            }, 300);
        });
        
        this.elements.searchClear.addEventListener('click', () => {
            this.elements.search.value = '';
            this.handleSearch('');
        });
        
        // 상세 정보 패널
        this.elements.closeDetails.addEventListener('click', () => {
            this.hideDetailsPanel();
        });
        
        // 리소스 타입 변경 (디바운싱 적용)
        let resourceTypeChangeTimeout;
        this.elements.resourceTypeRadios.forEach(radio => {
            radio.addEventListener('change', (e) => {
                if (e.target.checked) {
                    // 이전 타임아웃 클리어
                    if (resourceTypeChangeTimeout) {
                        clearTimeout(resourceTypeChangeTimeout);
                    }
                    
                    // 100ms 후에 실행 (빠른 클릭 방지)
                    resourceTypeChangeTimeout = setTimeout(() => {
                        this.handleResourceTypeChange(e.target.value);
                    }, 100);
                }
            });
        });
        
        // 컨트롤 버튼들
        this.elements.refreshBtn.addEventListener('click', () => this.refreshData());
        this.elements.fitBtn.addEventListener('click', () => this.fitGraph());
        this.elements.layoutBtn.addEventListener('click', () => this.changeLayout());
        this.elements.exportBtn.addEventListener('click', () => this.exportGraph());
        
        // 시뮬레이션 버튼
        const simulateBtn = document.getElementById('simulate-btn');
        if (simulateBtn) {
            simulateBtn.addEventListener('click', () => {
                this.runSimulation();
            });
        }
        
        // 키보드 단축키
        document.addEventListener('keydown', (e) => {
            if (e.ctrlKey || e.metaKey) {
                switch (e.key) {
                    case 'f':
                        e.preventDefault();
                        this.elements.search.focus();
                        break;
                    case 'r':
                        e.preventDefault();
                        this.refreshData();
                        break;
                    case 'l':
                        e.preventDefault();
                        this.changeLayout();
                        break;
                }
            }
            if (e.key === 'Escape') {
                this.hideDetailsPanel();
            }
        });
    }
    
    setupSocket() {
        this.socket = io();
        
        this.socket.on('connect', () => {
            console.log('Socket.IO 연결됨');
            this.updateConnectionStatus('connected', '연결됨');
        });
        
        this.socket.on('disconnect', () => {
            console.log('Socket.IO 연결 해제됨');
            this.updateConnectionStatus('disconnected', '연결 끊어짐');
        });
        
        this.socket.on('connected', (data) => {
            console.log('서버 연결 확인:', data);
            this.showToast(`서버에 연결되었습니다 (${data.version})`, 'success');
        });
        
        this.socket.on('data_changed', (data) => {
            console.log('데이터 변경 감지');
            this.updateGraphData(data);
            this.showToast('클러스터 변경사항이 감지되어 업데이트되었습니다.', 'info');
        });
        
        this.socket.on('error', (error) => {
            console.error('Socket.IO 오류:', error);
            this.showToast('서버 오류: ' + error.message, 'error');
        });
    }
    
    initCytoscape() {
        this.cy = cytoscape({
            container: this.elements.graph,
            
            style: [
                // 기본 노드 스타일
                {
                    selector: 'node',
                    style: {
                        'width': 60,
                        'height': 60,
                        'label': 'data(label)',
                        'text-valign': 'center',
                        'text-halign': 'center',
                        'font-size': '12px',
                        'font-weight': 'bold',
                        'color': '#2563eb',
                        'text-wrap': 'wrap',
                        'text-max-width': '80px',
                        'border-width': 2,
                        'border-color': '#e5e7eb',
                        'background-color': '#ffffff',
                        'overlay-padding': '6px',
                        'z-index': 10
                    }
                },
                
                // 정책 노드
                {
                    selector: 'node[group="policy"]',
                    style: {
                        'background-color': '#3b82f6',
                        'color': '#ffffff',
                        'border-color': '#1d4ed8',
                        'shape': 'diamond',
                        'width': 70,
                        'height': 70
                    }
                },
                
                // Pod 노드
                {
                    selector: 'node[group="pod"]',
                    style: {
                        'background-color': '#10b981',
                        'border-color': '#059669',
                        'shape': 'ellipse'
                    }
                },
                
                // Deployment 노드
                {
                    selector: 'node[group="deployment"]',
                    style: {
                        'background-color': '#8b5cf6',
                        'border-color': '#7c3aed',
                        'shape': 'hexagon'
                    }
                },
                
                // IP Block 노드
                {
                    selector: 'node[group="ipblock"]',
                    style: {
                        'background-color': '#f59e0b',
                        'border-color': '#d97706',
                        'shape': 'rectangle',
                        'width': 80,
                        'height': 40
                    }
                },
                
                // 외부 노드
                {
                    selector: 'node[group="external"]',
                    style: {
                        'background-color': '#f59e0b',
                        'border-color': '#d97706',
                        'shape': 'octagon',
                        'width': 80,
                        'height': 80,
                        'color': '#ffffff',
                        'font-weight': 'bold'
                    }
                },
                
                // 선택된 노드
                {
                    selector: 'node:selected',
                    style: {
                        'border-width': 4,
                        'border-color': '#ef4444',
                        'overlay-opacity': 0.2,
                        'overlay-color': '#ef4444'
                    }
                },
                
                // 하이라이트된 노드
                {
                    selector: 'node.highlighted',
                    style: {
                        'border-width': 4,
                        'border-color': '#f59e0b',
                        'overlay-opacity': 0.1,
                        'overlay-color': '#f59e0b'
                    }
                },
                
                // 숨겨진 노드
                {
                    selector: 'node.filtered',
                    style: {
                        'opacity': 0.2
                    }
                },
                
                // 기본 엣지 스타일
                {
                    selector: 'edge',
                    style: {
                        'width': 3,
                        'line-color': '#64748b',
                        'target-arrow-color': '#64748b',
                        'target-arrow-shape': 'triangle',
                        'curve-style': 'bezier',
                        'arrow-scale': 1.2,
                        'label': 'data(label)',
                        'font-size': '10px',
                        'text-rotation': 'autorotate',
                        'text-margin-y': -10,
                        'color': '#374151',
                        'text-background-color': '#ffffff',
                        'text-background-opacity': 0.8,
                        'text-background-padding': '2px'
                    }
                },
                
                // Ingress 엣지
                {
                    selector: 'edge[type="ingress"]',
                    style: {
                        'line-color': '#10b981',
                        'target-arrow-color': '#10b981',
                        'line-style': 'solid'
                    }
                },
                
                // Egress 엣지
                {
                    selector: 'edge[type="egress"]',
                    style: {
                        'line-color': '#3b82f6',
                        'target-arrow-color': '#3b82f6',
                        'line-style': 'dashed'
                    }
                },
                
                // IP Block 엣지
                {
                    selector: 'edge[type*="ipblock"]',
                    style: {
                        'line-color': '#f59e0b',
                        'target-arrow-color': '#f59e0b',
                        'line-style': 'dotted'
                    }
                },
                
                // 선택된 엣지
                {
                    selector: 'edge:selected',
                    style: {
                        'width': 5,
                        'line-color': '#ef4444',
                        'target-arrow-color': '#ef4444'
                    }
                },
                
                // 시뮬레이션 하이라이트
                {
                    selector: 'node.simulation-source',
                    style: {
                        'border-width': 4,
                        'border-color': '#10b981',
                        'overlay-opacity': 0.2,
                        'overlay-color': '#10b981'
                    }
                },
                
                {
                    selector: 'node.simulation-target',
                    style: {
                        'border-width': 4,
                        'border-color': '#3b82f6',
                        'overlay-opacity': 0.2,
                        'overlay-color': '#3b82f6'
                    }
                },
                
                {
                    selector: 'edge.simulation-path',
                    style: {
                        'width': 5,
                        'line-color': '#8b5cf6',
                        'target-arrow-color': '#8b5cf6',
                        'z-index': 999
                    }
                }
            ],
            
            layout: {
                name: 'cose-bilkent',
                animate: true,
                animationDuration: 1000,
                fit: true,
                padding: 50,
                randomize: false,
                nodeRepulsion: 4500,
                idealEdgeLength: 50,
                edgeElasticity: 0.45,
                nestingFactor: 0.1,
                gravity: 0.25,
                numIter: 2500,
                tile: true,
                animateFilter: function(node, i) { return true; }
            },
            
            minZoom: 0.3,
            maxZoom: 3,
            wheelSensitivity: 0.2
        });
        
        // 이벤트 리스너 추가
        this.cy.on('tap', 'node', (event) => {
            this.handleNodeClick(event.target);
        });
        
        this.cy.on('tap', (event) => {
            if (event.target === this.cy) {
                this.hideDetailsPanel();
            }
        });
        
        this.cy.on('mouseover', 'node', (event) => {
            this.highlightConnectedElements(event.target);
        });
        
        this.cy.on('mouseout', 'node', (event) => {
            this.removeHighlight();
        });
    }
    
    async loadInitialData() {
        const resourceType = this.getCurrentResourceType();
        console.log(`초기 데이터 로딩: ${resourceType}`);
        
        try {
            // 초기 로딩 시에는 isLoading 플래그를 리셋
            this.isLoading = false;
            await this.fetchGraphData(resourceType);
            console.log('초기 데이터 로딩 완료');
        } catch (error) {
            console.error('초기 데이터 로딩 실패:', error);
            this.showToast('초기 데이터 로딩에 실패했습니다: ' + error.message, 'error');
        } finally {
            // 확실히 로딩 상태 해제
            this.isLoading = false;
            this.hideLoading();
        }
    }
    
    async fetchGraphData(resourceType = 'pod') {
        // 이미 로딩 중이면 강제로 상태 리셋 후 진행
        if (this.isLoading) {
            console.log('이전 로딩 상태를 강제로 리셋합니다.');
            this.isLoading = false;
            this.hideLoading();
        }
        
        try {
            this.isLoading = true;
            console.log(`API 호출 시작: /api/data?resource_type=${resourceType}`);
            
            // 타임아웃을 위한 AbortController 생성
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 30000); // 30초 타임아웃
            
            const response = await fetch(`/api/data?resource_type=${resourceType}`, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                },
                signal: controller.signal
            });
            
            clearTimeout(timeoutId); // 성공시 타임아웃 클리어
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            console.log(`API 응답 성공: 노드 ${data.nodes?.length || 0}개`);
            
            this.updateGraphData(data);
            return data;
            
        } catch (error) {
            if (error.name === 'AbortError') {
                throw new Error('요청 시간이 초과되었습니다. 서버가 응답하지 않습니다.');
            }
            console.error('API 호출 실패:', error);
            throw error;
        } finally {
            // 확실히 로딩 상태 해제
            this.isLoading = false;
            console.log('fetchGraphData 완료, isLoading:', this.isLoading);
        }
    }
    
    updateGraphData(data) {
        console.log('그래프 데이터 업데이트 시작:', {
            resource_type: data.metadata?.resource_type,
            nodes: data.nodes?.length || 0,
            edges: data.edges?.length || 0,
            namespaces: data.namespaces?.length || 0
        });
        
        this.currentData = data;
        
        // Cytoscape 형식으로 변환
        const elements = this.transformDataToCytoscape(data);
        console.log('Cytoscape 요소 변환 완료:', elements.length);
        
        // 그래프 업데이트
        this.cy.elements().remove();
        this.cy.add(elements);
        console.log('그래프 요소 추가 완료');
        
        // 레이아웃 적용
        this.applyLayout();
        console.log('레이아웃 적용 완료');
        
        // 네임스페이스 필터 업데이트
        this.updateNamespaceFilters(data.namespaces || []);
        
        // 통계 업데이트
        this.updateStatistics(data);
        
        // 그래프 헤더 업데이트
        const resourceType = data.metadata?.resource_type || 'pod';
        const resourceCount = data.nodes?.filter(n => n.group === resourceType).length || 0;
        const resourceTypeLabel = resourceType === 'pod' ? 'Pod' : 'Deployment';
        this.updateGraphHeader(resourceTypeLabel, resourceCount);
        
        // 시뮬레이션 UI 업데이트
        this.updateSimulationUI(data.nodes);
        
        console.log('그래프 데이터 업데이트 완료:', {
            nodes: data.nodes?.length || 0,
            edges: data.edges?.length || 0,
            namespaces: data.namespaces?.length || 0
        });
    }
    
    transformDataToCytoscape(data) {
        const elements = [];
        
        // 노드 추가
        if (data.nodes) {
            data.nodes.forEach(node => {
                // 노드 라벨에 타입 정보 추가
                let displayLabel = node.label;
                if (node.group === 'pod') {
                    displayLabel = `🟢 ${node.label}`;
                } else if (node.group === 'deployment') {
                    displayLabel = `🟣 ${node.label}`;
                } else if (node.group === 'policy') {
                    displayLabel = `🔷 ${node.label}`;
                }
                
                elements.push({
                    data: {
                        id: node.id,
                        label: displayLabel,
                        group: node.group,
                        namespace: node.namespace,
                        status: node.status,
                        originalData: node
                    }
                });
            });
        }
        
        // 엣지 추가
        if (data.edges) {
            data.edges.forEach(edge => {
                const ports = edge.ports || 'All Ports';
                const typeIcon = edge.type === 'ingress' ? '📥' : edge.type === 'egress' ? '📤' : '🔗';
                const label = `${typeIcon} ${ports}`;
                
                elements.push({
                    data: {
                        id: edge.id || `${edge.source}-${edge.target}-${edge.type}`,
                        source: edge.source,
                        target: edge.target,
                        type: edge.type,
                        label: label,
                        ports: ports,
                        policy: edge.policy,
                        status: edge.status,
                        originalData: edge
                    }
                });
            });
        }
        
        return elements;
    }
    
    updateNamespaceFilters(namespaces) {
        const container = this.elements.namespaceFilters;
        container.innerHTML = '';
        
        // "All" 옵션 추가
        const allItem = this.createNamespaceFilterItem('all', 'All Namespaces', true);
        container.appendChild(allItem);
        
        // 네임스페이스별 필터 추가
        namespaces.forEach(namespace => {
            const item = this.createNamespaceFilterItem(namespace, namespace, true);
            container.appendChild(item);
        });
        
        // 카운트 업데이트
        if (this.elements.namespaceCount) {
            this.elements.namespaceCount.textContent = namespaces.length;
        }
    }
    
    createNamespaceFilterItem(value, label, checked) {
        const item = document.createElement('div');
        item.className = 'namespace-filter-item';
        
        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.id = `namespace-${value}`;
        checkbox.value = value;
        checkbox.checked = checked;
        checkbox.addEventListener('change', () => this.handleNamespaceFilter());
        
        const labelElement = document.createElement('label');
        labelElement.htmlFor = checkbox.id;
        labelElement.textContent = label;
        
        item.appendChild(checkbox);
        item.appendChild(labelElement);
        
        return item;
    }
    
    updateStatistics(data) {
        const policyCount = data.nodes?.filter(n => n.group === 'policy').length || 0;
        const resourceCount = data.nodes?.filter(n => n.group !== 'policy' && n.group !== 'ipblock').length || 0;
        const edgeCount = data.edges?.length || 0;
        
        // 현재 리소스 타입 가져오기
        const currentResourceType = data.metadata?.resource_type || this.getCurrentResourceType();
        const resourceTypeLabel = currentResourceType === 'pod' ? 'Pod' : 'Deployment';
        
        if (this.elements.policyCount) this.elements.policyCount.textContent = policyCount;
        if (this.elements.resourceCount) {
            this.elements.resourceCount.textContent = resourceCount;
            // 리소스 타입 라벨 업데이트
            const resourceLabel = document.querySelector('.status-item .status-label');
            if (resourceLabel && resourceLabel.textContent.includes('리소스')) {
                resourceLabel.textContent = `${resourceTypeLabel}:`;
            }
        }
        if (this.elements.edgeCount) this.elements.edgeCount.textContent = edgeCount;
        
        // 그래프 헤더에 현재 리소스 타입 표시
        this.updateGraphHeader(resourceTypeLabel, resourceCount);
    }
    
    updateGraphHeader(resourceType, count) {
        const graphHeader = document.querySelector('.graph-header');
        if (graphHeader) {
            // 기존 리소스 타입 표시 제거
            const existingTypeDisplay = graphHeader.querySelector('.current-resource-type');
            if (existingTypeDisplay) {
                existingTypeDisplay.remove();
            }
            
            // 새로운 리소스 타입 표시 추가
            const typeDisplay = document.createElement('div');
            typeDisplay.className = 'current-resource-type';
            typeDisplay.innerHTML = `
                <span class="resource-type-badge">
                    <span class="material-icons">${resourceType === 'Pod' ? 'dns' : 'apps'}</span>
                    현재 보기: ${resourceType} (${count}개)
                </span>
            `;
            
            // 그래프 컨트롤 앞에 삽입
            const graphControls = graphHeader.querySelector('.graph-controls');
            if (graphControls) {
                graphHeader.insertBefore(typeDisplay, graphControls);
            }
        }
    }
    
    handleNodeClick(node) {
        const nodeData = node.data('originalData');
        this.showNodeDetails(nodeData);
        
        // 노드 선택 표시
        this.cy.elements().removeClass('highlighted');
        node.addClass('highlighted');
        this.highlightConnectedElements(node);
    }
    
    async showNodeDetails(nodeData) {
        try {
            this.elements.detailsContent.innerHTML = '<div class="loading">상세 정보를 불러오는 중...</div>';
            this.showDetailsPanel();
            
            let detailsHtml = '';
            
            if (nodeData.group === 'policy') {
                const details = await this.fetchPolicyDetails(nodeData.id);
                detailsHtml = this.formatPolicyDetails(details || nodeData);
            } else if (nodeData.group === 'pod' || nodeData.group === 'deployment') {
                const details = await this.fetchResourceDetails(nodeData.group, nodeData.id);
                detailsHtml = this.formatResourceDetails(details || nodeData);
            } else {
                detailsHtml = this.formatGenericDetails(nodeData);
            }
            
            this.elements.detailsContent.innerHTML = detailsHtml;
            
        } catch (error) {
            console.error('상세 정보 로딩 실패:', error);
            this.elements.detailsContent.innerHTML = `
                <div class="error">
                    <span class="material-icons">error</span>
                    <p>상세 정보를 불러올 수 없습니다.</p>
                    <small>${error.message}</small>
                </div>
            `;
        }
    }
    
    async fetchPolicyDetails(policyId) {
        const response = await fetch(`/api/policy/${encodeURIComponent(policyId)}`);
        if (!response.ok) throw new Error(`정책 정보 조회 실패: ${response.statusText}`);
        return await response.json();
    }
    
    async fetchResourceDetails(resourceType, resourceId) {
        const response = await fetch(`/api/resource/${resourceType}/${encodeURIComponent(resourceId)}`);
        if (!response.ok) throw new Error(`리소스 정보 조회 실패: ${response.statusText}`);
        return await response.json();
    }
    
    formatPolicyDetails(policy) {
        return `
            <div class="detail-section">
                <h3><span class="material-icons">security</span> Network Policy</h3>
                <div class="detail-item">
                    <strong>Name:</strong> ${policy.metadata?.name || policy.label}
                </div>
                <div class="detail-item">
                    <strong>Namespace:</strong> ${policy.metadata?.namespace || policy.namespace}
                </div>
                <div class="detail-item">
                    <strong>UID:</strong> <code>${policy.metadata?.uid || 'N/A'}</code>
                </div>
            </div>
            
            <div class="detail-section">
                <h4><span class="material-icons">arrow_downward</span> Ingress Rules</h4>
                ${this.formatPolicyRules(policy.spec?.ingress || [], 'ingress')}
            </div>
            
            <div class="detail-section">
                <h4><span class="material-icons">arrow_upward</span> Egress Rules</h4>
                ${this.formatPolicyRules(policy.spec?.egress || [], 'egress')}
            </div>
            
            <div class="detail-section">
                <h4><span class="material-icons">label</span> Labels</h4>
                ${this.formatLabels(policy.metadata?.labels || {})}
            </div>
        `;
    }
    
    formatResourceDetails(resource) {
        const isDeployment = resource.kind === 'Deployment';
        
        return `
            <div class="detail-section">
                <h3><span class="material-icons">${isDeployment ? 'apps' : 'dns'}</span> ${resource.kind || 'Resource'}</h3>
                <div class="detail-item">
                    <strong>Name:</strong> ${resource.metadata?.name || resource.label}
                </div>
                <div class="detail-item">
                    <strong>Namespace:</strong> ${resource.metadata?.namespace || resource.namespace}
                </div>
                <div class="detail-item">
                    <strong>Status:</strong> <span class="status-badge">${resource.status?.phase || resource.status || 'Unknown'}</span>
                </div>
                <div class="detail-item">
                    <strong>Created:</strong> ${resource.metadata?.creation_timestamp ? new Date(resource.metadata.creation_timestamp).toLocaleString() : 'N/A'}
                </div>
            </div>
            
            ${isDeployment ? this.formatDeploymentStatus(resource.status) : ''}
            
            <div class="detail-section">
                <h4><span class="material-icons">label</span> Labels</h4>
                ${this.formatLabels(resource.metadata?.labels || {})}
            </div>
            
            <div class="detail-section">
                <h4><span class="material-icons">security</span> Applied Policies</h4>
                ${this.formatAppliedPolicies(resource.policies || [])}
            </div>
            
            ${resource.networkPolicyDetails ? this.formatNetworkPolicyDetails(resource.networkPolicyDetails) : ''}
        `;
    }
    
    formatGenericDetails(nodeData) {
        return `
            <div class="detail-section">
                <h3><span class="material-icons">info</span> ${nodeData.group.toUpperCase()}</h3>
                <div class="detail-item">
                    <strong>ID:</strong> <code>${nodeData.id}</code>
                </div>
                <div class="detail-item">
                    <strong>Label:</strong> ${nodeData.label}
                </div>
                <div class="detail-item">
                    <strong>Group:</strong> ${nodeData.group}
                </div>
                <div class="detail-item">
                    <strong>Status:</strong> <span class="status-badge">${nodeData.status}</span>
                </div>
            </div>
        `;
    }
    
    formatPolicyRules(rules, type) {
        if (!rules || rules.length === 0) {
            if (type === 'ingress') {
                return '<div class="no-data">🚫 모든 Ingress 트래픽 차단 (Deny All)</div>';
            } else {
                return '<div class="no-data">🚫 모든 Egress 트래픽 차단 (Deny All)</div>';
            }
        }
        
        return rules.map((rule, index) => {
            let ruleHtml = `<div class="rule-item"><strong>Rule ${index + 1}:</strong><div class="rule-details">`;
            
            // Ports 정보
            if (rule.ports && rule.ports.length > 0) {
                const portsStr = rule.ports.map(p => `${p.protocol || 'TCP'}:${p.port || 'All'}`).join(', ');
                ruleHtml += `<div><strong>🔌 Ports:</strong> <code>${portsStr}</code></div>`;
            } else {
                ruleHtml += `<div><strong>🔌 Ports:</strong> <code>All Ports</code></div>`;
            }
            
            // From/To 정보 (더 읽기 쉽게 포맷)
            if (type === 'ingress' && rule.from) {
                ruleHtml += `<div><strong>📥 From:</strong></div>`;
                rule.from.forEach(source => {
                    if (source.podSelector) {
                        if (Object.keys(source.podSelector).length === 0) {
                            ruleHtml += `<div class="rule-source">• 같은 네임스페이스의 모든 Pod</div>`;
                        } else if (source.podSelector.matchLabels) {
                            const labels = Object.entries(source.podSelector.matchLabels)
                                .map(([k, v]) => `${k}=${v}`).join(', ');
                            ruleHtml += `<div class="rule-source">• Pod 라벨: <code>${labels}</code></div>`;
                        }
                    }
                    if (source.namespaceSelector) {
                        if (Object.keys(source.namespaceSelector).length === 0) {
                            ruleHtml += `<div class="rule-source">• 모든 네임스페이스</div>`;
                        } else if (source.namespaceSelector.matchLabels) {
                            const labels = Object.entries(source.namespaceSelector.matchLabels)
                                .map(([k, v]) => `${k}=${v}`).join(', ');
                            ruleHtml += `<div class="rule-source">• 네임스페이스 라벨: <code>${labels}</code></div>`;
                        }
                    }
                    if (source.ipBlock) {
                        ruleHtml += `<div class="rule-source">• IP 블록: <code>${source.ipBlock.cidr}</code>`;
                        if (source.ipBlock.except) {
                            ruleHtml += ` (제외: <code>${source.ipBlock.except.join(', ')}</code>)`;
                        }
                        ruleHtml += `</div>`;
                    }
                });
            }
            
            if (type === 'egress' && rule.to) {
                ruleHtml += `<div><strong>📤 To:</strong></div>`;
                rule.to.forEach(destination => {
                    if (destination.podSelector) {
                        if (Object.keys(destination.podSelector).length === 0) {
                            ruleHtml += `<div class="rule-destination">• 같은 네임스페이스의 모든 Pod</div>`;
                        } else if (destination.podSelector.matchLabels) {
                            const labels = Object.entries(destination.podSelector.matchLabels)
                                .map(([k, v]) => `${k}=${v}`).join(', ');
                            ruleHtml += `<div class="rule-destination">• Pod 라벨: <code>${labels}</code></div>`;
                        }
                    }
                    if (destination.namespaceSelector) {
                        if (Object.keys(destination.namespaceSelector).length === 0) {
                            ruleHtml += `<div class="rule-destination">• 모든 네임스페이스</div>`;
                        } else if (destination.namespaceSelector.matchLabels) {
                            const labels = Object.entries(destination.namespaceSelector.matchLabels)
                                .map(([k, v]) => `${k}=${v}`).join(', ');
                            ruleHtml += `<div class="rule-destination">• 네임스페이스 라벨: <code>${labels}</code></div>`;
                        }
                    }
                    if (destination.ipBlock) {
                        ruleHtml += `<div class="rule-destination">• IP 블록: <code>${destination.ipBlock.cidr}</code>`;
                        if (destination.ipBlock.except) {
                            ruleHtml += ` (제외: <code>${destination.ipBlock.except.join(', ')}</code>)`;
                        }
                        ruleHtml += `</div>`;
                    }
                    if (Object.keys(destination).length === 0) {
                        ruleHtml += `<div class="rule-destination">• 모든 대상 (인터넷 포함)</div>`;
                    }
                });
            }
            
            ruleHtml += `</div></div>`;
            return ruleHtml;
        }).join('');
    }
    
    formatLabels(labels) {
        if (!labels || Object.keys(labels).length === 0) {
            return '<div class="no-data">라벨이 없습니다.</div>';
        }
        
        return Object.entries(labels).map(([key, value]) => `
            <div class="label-item">
                <code>${key}: ${value}</code>
            </div>
        `).join('');
    }
    
    formatAppliedPolicies(policies) {
        if (!policies || policies.length === 0) {
            return '<div class="no-data">⚠️ 적용된 정책이 없습니다. (기본적으로 모든 트래픽 허용)</div>';
        }
        
        return policies.map(policy => `
            <div class="policy-item">
                <span class="material-icons">policy</span>
                <code>${policy}</code>
            </div>
        `).join('');
    }
    
    formatNetworkPolicyDetails(details) {
        const securityLevelColor = {
            'High': '#e74c3c',
            'Medium': '#f39c12', 
            'Low': '#27ae60'
        };
        
        return `
            <div class="detail-section">
                <h4><span class="material-icons">analytics</span> Network Policy Analysis</h4>
                <div class="detail-item">
                    <strong>🛡️ Security Level:</strong> 
                    <span class="security-badge" style="background-color: ${securityLevelColor[details.securityLevel] || '#95a5a6'}">
                        ${details.securityLevel}
                    </span>
                </div>
                <div class="detail-item">
                    <strong>📊 Total Policies:</strong> ${details.totalPolicies}
                </div>
                <div class="detail-item">
                    <strong>🏷️ Policy Types:</strong> 
                    ${details.policyTypes.length > 0 ? 
                        details.policyTypes.map(type => `<span class="policy-type-badge">${type}</span>`).join(' ') : 
                        '<span class="no-policies">None</span>'
                    }
                </div>
            </div>
        `;
    }
    
    formatDeploymentStatus(status) {
        if (!status) return '';
        
        return `
            <div class="detail-section">
                <h4><span class="material-icons">analytics</span> Deployment Status</h4>
                <div class="detail-item">
                    <strong>Replicas:</strong> ${status.ready_replicas || 0}/${status.replicas || 0}
                </div>
                <div class="detail-item">
                    <strong>Available:</strong> ${status.available_replicas || 0}
                </div>
                <div class="detail-item">
                    <strong>Updated:</strong> ${status.updated_replicas || 0}
                </div>
            </div>
        `;
    }
    
    highlightConnectedElements(node) {
        this.cy.elements().removeClass('highlighted');
        
        const connectedEdges = node.connectedEdges();
        const connectedNodes = connectedEdges.connectedNodes();
        
        node.addClass('highlighted');
        connectedEdges.addClass('highlighted');
        connectedNodes.addClass('highlighted');
    }
    
    removeHighlight() {
        this.cy.elements().removeClass('highlighted');
    }
    
    handleSearch(query) {
        if (!query.trim()) {
            this.cy.nodes().removeClass('filtered');
            return;
        }
        
        const searchTerm = query.toLowerCase();
        this.cy.nodes().forEach(node => {
            const label = (node.data('label') || '').toLowerCase();
            const id = (node.data('id') || '').toLowerCase();
            const namespace = (node.data('namespace') || '').toLowerCase();
            
            const matches = label.includes(searchTerm) || 
                          id.includes(searchTerm) || 
                          namespace.includes(searchTerm);
            
            if (matches) {
                node.removeClass('filtered');
            } else {
                node.addClass('filtered');
            }
        });
    }
    
    handleNamespaceFilter() {
        const checkboxes = document.querySelectorAll('#namespace-filters input[type="checkbox"]');
        const selectedNamespaces = Array.from(checkboxes)
            .filter(cb => cb.checked)
            .map(cb => cb.value);
        
        console.log('네임스페이스 필터 적용:', selectedNamespaces);
        
        const showAll = selectedNamespaces.includes('all') || selectedNamespaces.length === 0;
        
        this.cy.nodes().forEach(node => {
            const nodeNamespace = node.data('namespace');
            const shouldShow = showAll || selectedNamespaces.includes(nodeNamespace);
            
            if (shouldShow) {
                node.removeClass('filtered');
                node.style('display', 'element');
            } else {
                node.addClass('filtered');
                node.style('display', 'none');
            }
        });
        
        // 레이아웃 재적용
        this.applyLayout();
        
        // 통계 업데이트
        const visibleNodes = this.cy.nodes().filter(node => !node.hasClass('filtered'));
        const visiblePolicies = visibleNodes.filter(node => node.data('group') === 'policy').length;
        const visibleResources = visibleNodes.filter(node => node.data('group') !== 'policy').length;
        
        document.getElementById('policy-count').textContent = visiblePolicies;
        document.getElementById('resource-count').textContent = visibleResources;
        
        this.showToast(`${selectedNamespaces.length > 0 ? selectedNamespaces.join(', ') : '모든'} 네임스페이스 필터 적용`, 'info');
    }
    
    async handleResourceTypeChange(resourceType) {
        console.log(`리소스 타입 변경 요청: ${resourceType}`);
        
        const resourceTypeLabel = resourceType === 'pod' ? 'Pod' : 'Deployment';
        
        try {
            console.log(`${resourceType} 데이터 로딩 시작`);
            this.showLoading(`${resourceTypeLabel} 데이터 로딩 중...`);
            
            const data = await this.fetchGraphData(resourceType);
            
            // 데이터 유효성 검사
            if (!data || !data.nodes) {
                throw new Error('서버에서 유효하지 않은 데이터를 반환했습니다.');
            }
            
            const resourceCount = data.nodes.filter(n => n.group === resourceType).length || 0;
            
            console.log(`${resourceType} 데이터 로딩 완료: ${resourceCount}개`);
            this.showToast(`✅ ${resourceTypeLabel} ${resourceCount}개가 로드되었습니다!`, 'success');
        } catch (error) {
            console.error('리소스 타입 변경 실패:', error);
            
            // 사용자 친화적인 오류 메시지
            let errorMessage = error.message;
            if (error.message.includes('이전 요청이 완료되지 않았습니다')) {
                errorMessage = '이전 요청이 처리 중입니다. 잠시만 기다려주세요.';
            } else if (error.message.includes('요청 시간이 초과')) {
                errorMessage = '서버 응답이 지연되고 있습니다. 잠시 후 다시 시도해주세요.';
            }
            
            this.showToast(`⚠️ ${resourceTypeLabel} 데이터 로드 실패: ${errorMessage}`, 'error', 8000);
        } finally {
            // 확실히 로딩 상태 해제
            this.isLoading = false;
            this.hideLoading();
            console.log('handleResourceTypeChange 완료, isLoading:', this.isLoading);
        }
    }
    
    getCurrentResourceType() {
        const checkedRadio = document.querySelector('input[name="resource_type"]:checked');
        return checkedRadio ? checkedRadio.value : 'pod';
    }
    
    async refreshData() {
        // 이미 로딩 중이면 요청 무시
        if (this.isLoading) {
            console.log('이미 로딩 중입니다. 새로고침 요청을 무시합니다.');
            return;
        }
        
        try {
            this.showLoading('데이터 새로고침 중...');
            
            // 캐시 클리어
            const response = await fetch('/api/cache/clear', { method: 'POST' });
            if (!response.ok) throw new Error('캐시 클리어 실패');
            
            // 데이터 새로고침
            const resourceType = this.getCurrentResourceType();
            await this.fetchGraphData(resourceType);
            
            this.showToast('데이터가 새로고침되었습니다.', 'success');
        } catch (error) {
            console.error('새로고침 실패:', error);
            this.showToast('새로고침에 실패했습니다: ' + error.message, 'error');
        } finally {
            this.hideLoading();
        }
    }
    
    fitGraph() {
        this.cy.fit();
        this.cy.center();
    }
    
    changeLayout() {
        this.currentLayoutIndex = (this.currentLayoutIndex + 1) % this.layouts.length;
        const layoutName = this.layouts[this.currentLayoutIndex];
        this.applyLayout(layoutName);
        this.showToast(`레이아웃이 ${layoutName}로 변경되었습니다.`, 'info');
    }
    
    applyLayout(layoutName = null) {
        const layout = layoutName || this.layouts[this.currentLayoutIndex];
        
        const layoutOptions = {
            name: layout,
            animate: true,
            animationDuration: 1000,
            fit: true,
            padding: 50
        };
        
        // 레이아웃별 추가 옵션
        if (layout === 'cose-bilkent') {
            Object.assign(layoutOptions, {
                nodeRepulsion: 4500,
                idealEdgeLength: 80,
                edgeElasticity: 0.45,
                nestingFactor: 0.1,
                gravity: 0.25,
                numIter: 2500,
                tile: true
            });
        }
        
        this.cy.layout(layoutOptions).run();
    }
    
    exportGraph() {
        try {
            // PNG로 내보내기
            const png = this.cy.png({
                scale: 2,
                full: true,
                bg: '#ffffff'
            });
            
            // 다운로드 링크 생성
            const link = document.createElement('a');
            link.download = `k8s-network-policy-${new Date().toISOString().slice(0, 10)}.png`;
            link.href = png;
            link.click();
            
            this.showToast('그래프가 PNG 파일로 내보내졌습니다.', 'success');
        } catch (error) {
            console.error('내보내기 실패:', error);
            this.showToast('내보내기에 실패했습니다: ' + error.message, 'error');
        }
    }
    
    showDetailsPanel() {
        this.elements.detailsPanel.classList.add('active');
    }
    
    hideDetailsPanel() {
        this.elements.detailsPanel.classList.remove('active');
        this.cy.elements().removeClass('highlighted');
    }
    
    showLoading(message = '로딩 중...') {
        this.isLoading = true;
        this.elements.loadingOverlay.querySelector('p').textContent = message;
        this.elements.loadingOverlay.classList.remove('hidden');
        console.log('showLoading 호출됨, isLoading:', this.isLoading, 'message:', message);
    }
    
    hideLoading() {
        this.isLoading = false;
        this.elements.loadingOverlay.classList.add('hidden');
        console.log('hideLoading 호출됨, isLoading:', this.isLoading);
    }
    
    updateConnectionStatus(status, text) {
        this.elements.connectionStatus.className = `status-indicator ${status}`;
        this.elements.connectionText.textContent = text;
    }
    
    showToast(message, type = 'info', duration = 5000) {
        const toastContainer = document.getElementById('toast-container');
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        
        const icon = {
            success: 'check_circle',
            error: 'error',
            warning: 'warning',
            info: 'info'
        }[type] || 'info';
        
        toast.innerHTML = `
            <span class="material-icons">${icon}</span>
            <span>${message}</span>
        `;
        
        toastContainer.appendChild(toast);
        
        // 자동 제거
        setTimeout(() => {
            toast.remove();
        }, duration);
        
        // 클릭으로 제거
        toast.addEventListener('click', () => {
            toast.remove();
        });
    }
    
    updateSimulationUI(nodes) {
        const sourceSelect = document.getElementById('source-select');
        const targetSelect = document.getElementById('target-select');
        
        if (!sourceSelect || !targetSelect) return;
        
        // 기존 옵션 제거 (첫 번째 옵션 제외)
        sourceSelect.innerHTML = '<option value="">소스 선택...</option>';
        targetSelect.innerHTML = '<option value="">타겟 선택...</option>';
        
        // 리소스 노드들만 필터링 (정책 노드 제외)
        const resourceNodes = nodes.filter(node => 
            node.group !== 'policy' && node.id && node.label
        );
        
        // 옵션 추가
        resourceNodes.forEach(node => {
            const option = document.createElement('option');
            option.value = node.id;
            option.textContent = `${node.label} (${node.namespace})`;
            
            sourceSelect.appendChild(option.cloneNode(true));
            targetSelect.appendChild(option);
        });
    }
    
    async runSimulation() {
        const sourceId = document.getElementById('source-select').value;
        const targetId = document.getElementById('target-select').value;
        const port = parseInt(document.getElementById('port-input').value) || 80;
        const protocol = document.getElementById('protocol-select').value;
        
        if (!sourceId || !targetId) {
            this.showToast('소스와 타겟을 모두 선택해주세요', 'warning');
            return;
        }
        
        if (sourceId === targetId) {
            this.showToast('소스와 타겟이 같을 수 없습니다', 'warning');
            return;
        }
        
        try {
            this.showLoading('통신 시뮬레이션 실행 중...');
            
            const response = await fetch('/api/simulate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    source: sourceId,
                    target: targetId,
                    port: port,
                    protocol: protocol
                })
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const result = await response.json();
            this.displaySimulationResult(result);
            this.highlightSimulationPath(sourceId, targetId, result.allowed);
            
        } catch (error) {
            console.error('시뮬레이션 오류:', error);
            this.showToast('시뮬레이션 실행 중 오류가 발생했습니다: ' + error.message, 'error');
        } finally {
            this.hideLoading();
        }
    }
    
    displaySimulationResult(result) {
        const resultContainer = document.getElementById('simulation-result');
        if (!resultContainer) return;
        
        resultContainer.style.display = 'block';
        resultContainer.className = `simulation-result ${result.allowed ? 'allowed' : 'blocked'}`;
        
        let html = `
            <div class="simulation-summary ${result.allowed ? 'allowed' : 'blocked'}">
                ${result.summary}
            </div>
            <div class="simulation-details">
                <strong>소스:</strong> ${result.source.name} (${result.source.namespace})<br>
                <strong>타겟:</strong> ${result.target.name} (${result.target.namespace})<br>
                <strong>포트:</strong> ${result.port} (${result.protocol})
            </div>
        `;
        
        if (result.policy_results && result.policy_results.length > 0) {
            html += '<div class="policy-results">';
            result.policy_results.forEach(policyResult => {
                html += `
                    <div class="policy-result-item ${policyResult.allowed ? 'allowed' : 'blocked'}">
                        <div class="policy-result-header">
                            ${policyResult.allowed ? '✅' : '❌'} ${policyResult.policy}
                        </div>
                        <div class="policy-result-reason">
                            ${policyResult.reason}
                        </div>
                        ${policyResult.ports_allowed && policyResult.ports_allowed.length > 0 ? 
                            `<div class="policy-result-ports">허용 포트: ${policyResult.ports_allowed.join(', ')}</div>` : ''}
                    </div>
                `;
            });
            html += '</div>';
        }
        
        if (result.recommendations && result.recommendations.length > 0) {
            html += '<div class="recommendations">';
            result.recommendations.forEach(rec => {
                html += `
                    <div class="recommendation-item">
                        <div class="recommendation-title">${rec.title}</div>
                        <div class="recommendation-description">${rec.description}</div>
                    </div>
                `;
            });
            html += '</div>';
        }
        
        resultContainer.innerHTML = html;
    }
    
    highlightSimulationPath(sourceId, targetId, allowed) {
        // 기존 하이라이트 제거
        this.cy.elements().removeClass('simulation-source simulation-target simulation-path');
        
        // 소스와 타겟 노드 하이라이트
        this.cy.getElementById(sourceId).addClass('simulation-source');
        this.cy.getElementById(targetId).addClass('simulation-target');
        
        // 연결 엣지 하이라이트
        const edges = this.cy.edges().filter(edge => {
            return (edge.source().id() === sourceId && edge.target().id() === targetId) ||
                   (edge.source().id() === targetId && edge.target().id() === sourceId);
        });
        
        edges.addClass('simulation-path');
        
        // 결과에 따라 스타일 조정
        if (!allowed) {
            edges.style({
                'line-color': '#ef4444',
                'target-arrow-color': '#ef4444',
                'line-style': 'dotted'
            });
        }
        
        // 3초 후 하이라이트 제거
        setTimeout(() => {
            this.cy.elements().removeClass('simulation-source simulation-target simulation-path');
            edges.removeStyle();
        }, 3000);
    }
}

// 애플리케이션 초기화
document.addEventListener('DOMContentLoaded', () => {
    console.log('Kubernetes Network Policy Visualizer 2.0 시작');
    new NetworkPolicyVisualizer();
});

// CSS 스타일 추가
const additionalStyles = `
    .detail-section {
        margin-bottom: 1.5rem;
        padding-bottom: 1rem;
        border-bottom: 1px solid var(--border-color);
    }
    
    .detail-section:last-child {
        border-bottom: none;
    }
    
    .detail-section h3,
    .detail-section h4 {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        margin-bottom: 1rem;
        color: var(--primary-color);
        font-size: 1rem;
        font-weight: 600;
    }
    
    .detail-item {
        margin-bottom: 0.75rem;
        line-height: 1.5;
    }
    
    .detail-item strong {
        color: var(--text-primary);
        margin-right: 0.5rem;
    }
    
    .status-badge {
        padding: 2px 8px;
        border-radius: 12px;
        background: var(--success-color);
        color: white;
        font-size: 0.75rem;
        font-weight: 500;
    }
    
    .rule-item,
    .label-item,
    .policy-item {
        background: var(--bg-tertiary);
        padding: 0.75rem;
        border-radius: 6px;
        margin-bottom: 0.5rem;
    }
    
    .rule-details {
        margin-top: 0.5rem;
        font-size: 0.875rem;
        color: var(--text-secondary);
    }
    
    .no-data {
        color: var(--text-muted);
        font-style: italic;
        text-align: center;
        padding: 1rem;
    }
    
    .error {
        text-align: center;
        color: var(--error-color);
        padding: 2rem;
    }
    
    .error .material-icons {
        font-size: 3rem;
        margin-bottom: 1rem;
        opacity: 0.5;
    }
    
    .loading {
        text-align: center;
        padding: 2rem;
        color: var(--text-secondary);
    }
    
    code {
        background: var(--bg-tertiary);
        padding: 2px 6px;
        border-radius: 4px;
        font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
        font-size: 0.875rem;
    }
    
    .rule-source, .rule-destination {
        margin-left: 1rem;
        margin-bottom: 0.25rem;
        color: var(--text-secondary);
        font-size: 0.875rem;
    }
    
    .security-badge {
        padding: 2px 8px;
        border-radius: 12px;
        color: white;
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
    }
    
    .policy-type-badge {
        display: inline-block;
        padding: 2px 6px;
        margin: 2px;
        background: var(--primary-color);
        color: white;
        border-radius: 8px;
        font-size: 0.75rem;
        font-weight: 500;
    }
    
    .policy-item {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        background: var(--bg-tertiary);
        padding: 0.75rem;
        border-radius: 6px;
        margin-bottom: 0.5rem;
    }
    
    .policy-item .material-icons {
        font-size: 1rem;
        color: var(--primary-color);
    }
    
    .no-policies {
        color: var(--text-muted);
        font-style: italic;
    }
`;

// 스타일 추가
const styleSheet = document.createElement('style');
styleSheet.textContent = additionalStyles;
document.head.appendChild(styleSheet);

class CommunicationMatrix {
    constructor() {
        this.matrixElement = document.getElementById('communication-matrix');
        this.searchInput = document.getElementById('resource-search');
        this.namespaceSelect = document.getElementById('namespace-select');
        this.resourceData = [];
        this.communicationCache = new Map();
        this.currentResourceType = 'deployment';
        
        // 가상 스크롤링 관련 설정 추가
        this.pageSize = 30;
        this.currentPage = 0;
        this.visibleRows = new Set();
        this.rowHeight = 40;
        
        // 필터링 상태
        this.filters = {
            namespaces: new Set(),
            search: '',
            showSystemPods: false
        };

        this.initializeEventListeners();
    }

    initializeEventListeners() {
        if (this.searchInput) {
            this.searchInput.addEventListener('input', () => this.handleSearch());
        }
        if (this.namespaceSelect) {
            this.namespaceSelect.addEventListener('change', () => this.handleNamespaceFilter());
        }
        
        this.matrixElement.querySelector('tbody')?.addEventListener('scroll', this.handleScroll.bind(this));
        
        document.getElementById('show-system-pods')?.addEventListener('change', (e) => {
            this.filters.showSystemPods = e.target.checked;
            this.renderMatrix();
        });

        document.getElementById('view-mode')?.addEventListener('change', (e) => {
            this.currentViewMode = e.target.value;
            this.renderMatrix();
        });
    }

    isSystemResource(resourceName) {
        const systemPrefixes = ['calico-', 'aws-', 'kube-', 'csi-', 'ebs-'];
        return systemPrefixes.some(prefix => resourceName.toLowerCase().startsWith(prefix));
    }

    getFilteredData() {
        return this.resourceData.filter(resource => {
            if (!this.filters.showSystemPods && this.isSystemResource(resource.data.label)) {
                return false;
            }
            if (this.filters.search && !resource.data.label.toLowerCase().includes(this.filters.search.toLowerCase())) {
                return false;
            }
            if (this.filters.namespaces.size > 0) {
                const namespace = resource.data.id.split('/')[0];
                if (!this.filters.namespaces.has(namespace)) {
                    return false;
                }
            }
            return true;
        });
    }

    async renderMatrix() {
        const headerRow = this.matrixElement.querySelector('thead tr');
        headerRow.innerHTML = '<th class="corner-header">From ↓ / To →</th>';
        
        // 필터링된 데이터 가져오기
        const filteredData = this.getFilteredData();
        
        // 헤더 생성 (고정)
        filteredData.forEach(resource => {
            const th = document.createElement('th');
            th.textContent = resource.data.label;
            th.title = resource.data.id;
            th.className = 'matrix-header';
            headerRow.appendChild(th);
        });

        const tbody = this.matrixElement.querySelector('tbody');
        tbody.innerHTML = '';

        // 가상 스크롤링을 위한 전체 높이 설정
        const totalHeight = filteredData.length * this.rowHeight;
        const virtualScroller = document.createElement('div');
        virtualScroller.style.height = `${totalHeight}px`;
        virtualScroller.className = 'virtual-scroller';
        tbody.appendChild(virtualScroller);

        // 현재 뷰포트에 표시할 행들만 렌더링
        this.renderVisibleRows(filteredData);
    }

    renderVisibleRows(filteredData) {
        const tbody = this.matrixElement.querySelector('tbody');
        const scrollTop = tbody.scrollTop;
        const viewportHeight = tbody.clientHeight;
        
        const startIndex = Math.floor(scrollTop / this.rowHeight);
        const endIndex = Math.min(
            startIndex + Math.ceil(viewportHeight / this.rowHeight) + 1,
            filteredData.length
        );

        // 이미 렌더링된 행은 건너뛰기
        for (let i = startIndex; i < endIndex; i++) {
            if (this.visibleRows.has(i)) continue;
            
            const source = filteredData[i];
            const row = this.createMatrixRow(source, filteredData);
            row.style.position = 'absolute';
            row.style.top = `${i * this.rowHeight}px`;
            this.matrixElement.querySelector('.virtual-scroller').appendChild(row);
            this.visibleRows.add(i);
        }

        // 뷰포트를 벗어난 행 제거
        this.visibleRows.forEach(index => {
            if (index < startIndex || index >= endIndex) {
                const row = this.matrixElement.querySelector(`[data-row-index="${index}"]`);
                if (row) row.remove();
                this.visibleRows.delete(index);
            }
        });
    }

    handleScroll(event) {
        window.requestAnimationFrame(() => {
            this.renderVisibleRows(this.getFilteredData());
        });
    }

    async loadData() {
        try {
            showLoading();
            const resourceType = document.querySelector('input[name="matrix_resource_type"]:checked')?.value || 'deployment';
            const response = await fetch(`/data?resource_type=${resourceType}`);
            const data = await response.json();

            if (!data.nodes) {
                throw new Error('No nodes data received');
            }

            this.resourceData = data.nodes.filter(node => 
                node.data.group === 'deployment' || node.data.group === 'pod'
            );
            
            await this.renderMatrix();
            this.populateNamespaceFilter();
            hideLoading();
        } catch (error) {
            console.error('Error loading data:', error);
            hideLoading();
        }
    }

    createMatrixRow(source, filteredData) {
        const tr = document.createElement('tr');
        tr.dataset.rowIndex = filteredData.indexOf(source);
        
        const tdLabel = document.createElement('td');
        tdLabel.textContent = source.data.label;
        tdLabel.title = source.data.id;
        tdLabel.className = 'fixed-column';
        tr.appendChild(tdLabel);

        filteredData.forEach(target => {
            const td = this.createMatrixCell(source, target);
            tr.appendChild(td);
        });

        return tr;
    }

    createMatrixCell(source, target) {
        const td = document.createElement('td');
        td.classList.add('matrix-cell');
        td.dataset.source = source.data.id;
        td.dataset.target = target.data.id;
        td.textContent = '•';
        
        if (source.data.id === target.data.id) {
            td.classList.add('same-resource');
            td.textContent = '-';
        } else {
            td.addEventListener('click', () => this.handleCellClick(td));
        }
        
        return td;
    }

    async handleCellClick(cell) {
        const sourceId = cell.dataset.source;
        const targetId = cell.dataset.target;
        const cacheKey = `${sourceId}-${targetId}-${this.currentResourceType}`;

        try {
            let communication;
            if (this.communicationCache.has(cacheKey)) {
                communication = this.communicationCache.get(cacheKey);
            } else {
                cell.textContent = '...';
                communication = await this.analyzeCommunication(sourceId, targetId);
                
                if (communication) {
                    this.communicationCache.set(cacheKey, communication);
                }
            }

            if (!communication) {
                throw new Error('Failed to analyze communication');
            }

            this.updateCellDisplay(cell, communication);
            this.showCommunicationDetails(cell, communication);
        } catch (error) {
            console.error('Error in handleCellClick:', error);
            cell.textContent = '!';
            cell.title = 'Error: ' + error.message;
            
            const detailsContainer = document.getElementById('matrix-cell-details');
            if (detailsContainer) {
                detailsContainer.innerHTML = `
                    <h4>Error Analysis Details</h4>
                    <p><strong>Source:</strong> ${sourceId}</p>
                    <p><strong>Target:</strong> ${targetId}</p>
                    <p><strong>Error:</strong> ${error.message}</p>
                `;
            }
        }
    }

    async analyzeCommunication(source, target) {
        try {
            const response = await fetch(
                `/check-communication?source=${encodeURIComponent(source)}` +
                `&target=${encodeURIComponent(target)}` +
                `&resource_type=${this.currentResourceType}`
            );
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            return await response.json();
        } catch (error) {
            console.error('Error analyzing communication:', error);
            return null;
        }
    }

    updateCellDisplay(cell, communication) {
        cell.classList.remove('allowed', 'blocked', 'no-policy');
        
        if (!communication) {
            cell.classList.add('no-policy');
            cell.textContent = '-';
            return;
        }

        if (communication.allowed) {
            cell.classList.add('allowed');
            cell.textContent = '✓';
            
            let tooltip = 'Allowed\n';
            if (communication.ports?.length > 0) {
                tooltip += `Ports: ${communication.ports.join(', ')}\n`;
            }
            if (communication.policies?.length > 0) {
                tooltip += '\nAllowing Policies:\n';
                communication.policies
                    .filter(p => p.type === 'allow')
                    .forEach(p => tooltip += `- ${p.name}\n`);
            }
            cell.title = tooltip;
        } else {
            cell.classList.add('blocked');
            cell.textContent = '✗';
            
            let tooltip = `Blocked\n${communication.reason}\n`;
            if (communication.policies?.length > 0) {
                tooltip += '\nBlocking Policies:\n';
                communication.policies
                    .filter(p => p.type === 'block')
                    .forEach(p => tooltip += `- ${p.name}\n`);
            }
            cell.title = tooltip;
        }
    }

    showCommunicationDetails(cell, result) {
        const detailsContainer = document.getElementById('matrix-cell-details');
        const sourceId = cell.dataset.source;
        const targetId = cell.dataset.target;
        const sourceLabel = this.resourceData.find(r => r.data.id === sourceId)?.data.label;
        const targetLabel = this.resourceData.find(r => r.data.id === targetId)?.data.label;

        let html = `
            <h4>Communication Analysis</h4>
            <p><strong>From:</strong> ${sourceLabel} (${sourceId})</p>
            <p><strong>To:</strong> ${targetLabel} (${targetId})</p>
            <p><strong>Status:</strong> <span class="${result.allowed ? 'allowed' : 'blocked'}">${result.allowed ? 'Allowed' : 'Blocked'}</span></p>
        `;

        if (result.allowed) {
            html += `
                <h5>Allowed Ports</h5>
                <ul class="ports-list">
                    ${result.ports.map(port => `<li>${port}</li>`).join('')}
                </ul>
            `;

            if (result.policies?.length > 0) {
                const allowPolicies = result.policies.filter(p => p.type === 'allow');
                if (allowPolicies.length > 0) {
                    html += `
                        <h5>Allowing Policies</h5>
                        <ul class="policy-list">
                            ${allowPolicies.map(policy => `<li>${policy.name}</li>`).join('')}
                        </ul>
                    `;
                }
            }
        } else {
            if (result.policies?.length > 0) {
                const blockPolicies = result.policies.filter(p => p.type === 'block');
                if (blockPolicies.length > 0) {
                    html += `
                        <h5>Blocking Policies</h5>
                        <ul class="policy-list">
                            ${blockPolicies.map(policy => `<li>${policy.name}</li>`).join('')}
                        </ul>
                    `;
                }
            }
        }

        detailsContainer.innerHTML = html;
    }

    populateNamespaceFilter() {
        const namespaces = new Set();
        this.resourceData.forEach(resource => {
            const namespace = resource.data.id.split('/')[0];
            namespaces.add(namespace);
        });

        this.namespaceSelect.innerHTML = '';
        namespaces.forEach(namespace => {
            const option = document.createElement('option');
            option.value = namespace;
            option.textContent = namespace;
            option.selected = true;
            this.namespaceSelect.appendChild(option);
        });
    }

    handleSearch() {
        this.filters.search = this.searchInput.value.toLowerCase();
        this.renderMatrix();
    }

    handleNamespaceFilter() {
        this.filters.namespaces = new Set(
            Array.from(this.namespaceSelect.selectedOptions).map(option => option.value)
        );
        this.renderMatrix();
    }
}

const style = document.createElement('style');
style.textContent = `
   .matrix-container {
       position: relative;
       overflow: hidden;
       height: 80vh;
   }

   .matrix-wrapper {
       position: relative;
       overflow: auto;
       height: 100%;
   }

   .virtual-scroller {
       position: relative;
   }

   .matrix-row {
       position: absolute;
       left: 0;
       right: 0;
       height: 40px;
   }

   .matrix-cell {
       height: 40px;
       line-height: 40px;
       text-align: center;
       min-width: 60px;
       cursor: pointer;
       transition: background-color 0.2s;
       border: 1px solid #dee2e6;
   }

   .matrix-header {
       position: sticky;
       top: 0;
       background: white;
       z-index: 1;
       padding: 10px;
       border: 1px solid #dee2e6;
   }

   .fixed-column {
       position: sticky;
       left: 0;
       background: white;
       z-index: 2;
       padding: 10px;
       border: 1px solid #dee2e6;
   }

   .matrix-cell:hover {
       background-color: rgba(0, 0, 0, 0.05);
   }

   .matrix-cell.allowed {
       background-color: #e3ffe3;
       color: #2ECC40;
   }

   .matrix-cell.blocked {
       background-color: #ffe3e3;
       color: #FF4136;
   }

   .matrix-cell.no-policy {
       background-color: #f0f0f0;
       color: #666;
   }

   .details-container {
       padding: 20px;
       background: white;
       border-left: 1px solid #dee2e6;
   }

   .allowed {
       color: #2ECC40;
   }

   .blocked {
       color: #FF4136;
   }
`;
document.head.appendChild(style);

function showLoading() {
   const overlay = document.getElementById('loading-overlay');
   if (overlay) overlay.style.display = 'flex';
}

function hideLoading() {
   const overlay = document.getElementById('loading-overlay');
   if (overlay) overlay.style.display = 'none';
}

// 탭 전환 및 매트릭스 초기화
document.addEventListener('DOMContentLoaded', () => {
   const tabButtons = document.querySelectorAll('.tab-button');
   const viewContainers = document.querySelectorAll('.view-container');
   let matrixInstance = null;

   tabButtons.forEach(button => {
       button.addEventListener('click', () => {
           const viewName = button.dataset.view;
           
           tabButtons.forEach(btn => btn.classList.remove('active'));
           button.classList.add('active');
           
           viewContainers.forEach(container => {
               if (container.id === `${viewName}-view`) {
                   container.style.display = 'block';
                   if (viewName === 'matrix' && !matrixInstance) {
                       matrixInstance = new CommunicationMatrix();
                       matrixInstance.loadData();
                   }
               } else {
                   container.style.display = 'none';
               }
           });
       });
   });
});
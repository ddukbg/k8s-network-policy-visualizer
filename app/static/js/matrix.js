/* matrix.js 전체 내용을 이것으로 교체 */

class CommunicationMatrix {
    constructor() {
        this.matrixElement = document.getElementById('communication-matrix');
        this.searchInput = document.getElementById('resource-search');
        this.namespaceSelect = document.getElementById('namespace-select');
        this.resourceData = [];
        this.communicationCache = new Map();
        this.initializeEventListeners();
    }

    initializeEventListeners() {
        if (this.searchInput) {
            this.searchInput.addEventListener('input', () => this.handleSearch());
        }
        if (this.namespaceSelect) {
            this.namespaceSelect.addEventListener('change', () => this.handleNamespaceFilter());
        }
    }

    async loadData() {
        console.log('Loading matrix data...');
        try {
            showLoading();
            const resourceType = document.querySelector('input[name="matrix_resource_type"]:checked')?.value || 'deployment';
            const response = await fetch(`/data?resource_type=${resourceType}`);
            const data = await response.json();
            console.log('Received data:', data);

            if (!data.nodes) {
                throw new Error('No nodes data received');
            }

            this.resourceData = data.nodes;
            console.log('Resource data loaded:', this.resourceData.length, 'nodes');
            await this.renderMatrix();
            this.populateNamespaceFilter();
            hideLoading();
        } catch (error) {
            console.error('Error loading data:', error);
            hideLoading();
        }
    }

    async renderMatrix() {
        const headerRow = this.matrixElement.querySelector('thead tr');
        headerRow.innerHTML = '<th class="corner-header">From ↓ / To →</th>';
        
        this.resourceData.forEach(resource => {
            const th = document.createElement('th');
            th.textContent = resource.data.label;
            th.title = resource.data.id;
            headerRow.appendChild(th);
        });

        const tbody = this.matrixElement.querySelector('tbody');
        tbody.innerHTML = '';

        // 행 생성을 chunk로 나눠서 처리
        const chunkSize = 10;
        for (let i = 0; i < this.resourceData.length; i += chunkSize) {
            const chunk = this.resourceData.slice(i, i + chunkSize);
            await new Promise(resolve => {
                requestAnimationFrame(() => {
                    chunk.forEach(source => {
                        const tr = this.createMatrixRow(source);
                        tbody.appendChild(tr);
                    });
                    resolve();
                });
            });
        }
    }

    createMatrixRow(source) {
        const tr = document.createElement('tr');
        
        const tdLabel = document.createElement('td');
        tdLabel.textContent = source.data.label;
        tdLabel.title = source.data.id;
        tr.appendChild(tdLabel);

        this.resourceData.forEach(target => {
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
        
        td.addEventListener('click', () => this.handleCellClick(td));
        
        return td;
    }

    async handleCellClick(cell) {
        const sourceId = cell.dataset.source;
        const targetId = cell.dataset.target;
        const cacheKey = `${sourceId}-${targetId}`;

        try {
            let communication;
            if (this.communicationCache.has(cacheKey)) {
                communication = this.communicationCache.get(cacheKey);
            } else {
                cell.textContent = '...';
                communication = await this.analyzeCommunication(sourceId, targetId);
                this.communicationCache.set(cacheKey, communication);
            }

            this.updateCellDisplay(cell, communication);
            this.showCommunicationDetails(sourceId, targetId, communication);
        } catch (error) {
            console.error('Error handling cell click:', error);
            cell.textContent = '!';
        }
    }

    async analyzeCommunication(source, target) {
        try {
            const response = await fetch(`/check-communication?source=${encodeURIComponent(source)}&target=${encodeURIComponent(target)}`);
            return await response.json();
        } catch (error) {
            console.error('Error checking communication:', error);
            return null;
        }
    }

    updateCellDisplay(cell, communication) {
        cell.classList.remove('no-policy', 'allowed', 'blocked');
        
        if (!communication) {
            cell.classList.add('no-policy');
            cell.textContent = '-';
            return;
        }

        cell.classList.add(communication.allowed ? 'allowed' : 'blocked');
        cell.textContent = communication.allowed ? '✓' : '✗';
        
        if (communication.allowed && communication.ports && communication.ports.length > 0) {
            cell.title = `Ports: ${communication.ports.join(', ')}`;
        }
    }

    showCommunicationDetails(source, target, communication) {
        const detailsContainer = document.getElementById('matrix-cell-details');
        if (!detailsContainer) return;

        const sourceLabel = this.resourceData.find(r => r.data.id === source)?.data.label;
        const targetLabel = this.resourceData.find(r => r.data.id === target)?.data.label;

        let html = `
            <h4>Communication Details</h4>
            <p><strong>From:</strong> ${sourceLabel} (${source})</p>
            <p><strong>To:</strong> ${targetLabel} (${target})</p>
            <p><strong>Status:</strong> <span class="${communication.allowed ? 'allowed' : 'blocked'}">${communication.allowed ? 'Allowed' : 'Blocked'}</span></p>
        `;

        if (communication.allowed && communication.ports) {
            html += `
                <h5>Allowed Ports</h5>
                <ul>
                    ${communication.ports.map(port => `<li>${port}</li>`).join('')}
                </ul>
            `;
        }

        if (communication.ingress_policies?.length > 0) {
            html += `
                <h5>Ingress Policies</h5>
                <ul>
                    ${communication.ingress_policies.map(policy => `<li>${policy}</li>`).join('')}
                </ul>
            `;
        }

        if (communication.egress_policies?.length > 0) {
            html += `
                <h5>Egress Policies</h5>
                <ul>
                    ${communication.egress_policies.map(policy => `<li>${policy}</li>`).join('')}
                </ul>
            `;
        }

        detailsContainer.innerHTML = html;
    }

    handleSearch() {
        const searchTerm = this.searchInput.value.toLowerCase();
        const rows = this.matrixElement.querySelectorAll('tbody tr');
        
        rows.forEach(row => {
            const label = row.querySelector('td:first-child').textContent.toLowerCase();
            if (label.includes(searchTerm)) {
                row.style.display = '';
            } else {
                row.style.display = 'none';
            }
        });
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

    handleNamespaceFilter() {
        const selectedNamespaces = Array.from(this.namespaceSelect.selectedOptions).map(option => option.value);
        const rows = this.matrixElement.querySelectorAll('tbody tr');
        
        rows.forEach(row => {
            const sourceNamespace = row.querySelector('td:first-child').textContent.split('.')[0];
            if (selectedNamespaces.includes(sourceNamespace)) {
                row.style.display = '';
            } else {
                row.style.display = 'none';
            }
        });
    }
}

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
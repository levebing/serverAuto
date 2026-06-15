// ========== 动态粒子系统 ==========
class ParticleSystem {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.particles = [];
        this.particleCount = 80;
        this.init();
    }

    init() {
        // 确保容器存在
        if (!this.container) {
            console.warn('粒子容器不存在，跳过粒子初始化');
            return;
        }

        for (let i = 0; i < this.particleCount; i++) {
            this.createParticle();
        }
        this.animate();
    }

    createParticle() {
        const particle = document.createElement('div');
        const size = Math.random() * 3 + 1;
        const opacity = Math.random() * 0.5 + 0.3;
        
        particle.style.cssText = `
            position: absolute;
            width: ${size}px;
            height: ${size}px;
            background: rgba(73, 160, 255, ${opacity});
            border-radius: 50%;
            box-shadow: 0 0 ${Math.random() * 5 + 2}px rgba(73, 160, 255, 0.5);
            pointer-events: none;
        `;
        this.container.appendChild(particle);
        
        this.particles.push({
            el: particle,
            x: Math.random() * window.innerWidth,
            y: Math.random() * window.innerHeight,
            vx: (Math.random() - 0.5) * 0.5,
            vy: (Math.random() - 0.5) * 0.5,
            life: Math.random() * 100 + 100
        });
    }

    animate() {
        this.particles.forEach(p => {
            p.x += p.vx;
            p.y += p.vy;
            p.life--;

            // 重置粒子位置
            if (p.life <= 0 || p.x < 0 || p.x > window.innerWidth || p.y < 0 || p.y > window.innerHeight) {
                p.x = Math.random() * window.innerWidth;
                p.y = Math.random() * window.innerHeight;
                p.life = Math.random() * 100 + 100;
            }

            p.el.style.left = p.x + 'px';
            p.el.style.top = p.y + 'px';
            p.el.style.opacity = p.life / 200;
        });

        requestAnimationFrame(() => this.animate());
    }
}

// ========== 页面加载完成后初始化粒子系统 ==========
document.addEventListener('DOMContentLoaded', function() {
    // 初始化粒子系统
    new ParticleSystem('particles-js');

    // 创建科技网格背景
    if (!document.querySelector('.bg-grid')) {
        const grid = document.createElement('div');
        grid.className = 'bg-grid';
        document.body.appendChild(grid);
    }

    // 创建流光效果
    if (!document.querySelector('.light-stream')) {
        const stream = document.createElement('div');
        stream.className = 'light-stream';
        document.body.appendChild(stream);
    }
});

// ========== 工具函数：创建背景元素 ==========
function createTechBackground() {
    // 创建粒子容器
    if (!document.getElementById('particles-js')) {
        const particleContainer = document.createElement('div');
        particleContainer.id = 'particles-js';
        document.body.insertBefore(particleContainer, document.body.firstChild);
    }

    // 创建网格背景
    if (!document.querySelector('.bg-grid')) {
        const grid = document.createElement('div');
        grid.className = 'bg-grid';
        document.body.appendChild(grid);
    }

    // 创建流光效果
    if (!document.querySelector('.light-stream')) {
        const stream = document.createElement('div');
        stream.className = 'light-stream';
        document.body.appendChild(stream);
    }

    // 初始化粒子系统
    setTimeout(() => {
        new ParticleSystem('particles-js');
    }, 100);
}
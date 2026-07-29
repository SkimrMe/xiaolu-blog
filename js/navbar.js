// 导航栏渲染逻辑 Vue3 版本
fetch('data/navbar.json')
.then(response => response.json())
.then(data => {
    // 获取当前页面文件名，用于高亮active
    const path = window.location.pathname;
    let currentPage = path.split('/').pop();
    // 根路径（如https://xxx.com/ 或 https://xxx.com/xiaolu-blog/）默认是index.html
    if (currentPage === '' || currentPage === 'xiaolu-blog/') {
        currentPage = 'index.html';
    }
    // 处理GitHub Pages子路径情况
    if (currentPage.includes('/')) {
        currentPage = currentPage.split('/').pop();
    }

    // Vue3 应用初始化
    Vue.createApp({
        data() {
            return {
                list: data,
                currentPage: currentPage
            };
        }
    }).mount('#main-navbar');
})
.catch(err => {
    console.error('导航栏加载失败:', err);
    // 降级处理：如果加载失败，显示默认静态导航
    const ul = document.querySelector('#main-navbar');
    if (ul) {
        ul.innerHTML = `
            <li><a href="index.html">首页</a></li>
            <li><a href="articles.html">文章</a></li>
            <li><a href="diary.html">日记</a></li>
            <li><a href="gallery.html">相册</a></li>
            <li><a href="video.html">视频</a></li>
            <li><a href="game.html">🎮 小游戏</a></li>
            <li><a href="memories.html">回忆</a></li>
            <li><a href="rumors.html">💬 留言墙</a></li>
            <li><a href="about.html">关于</a></li>
        `;
    }
});

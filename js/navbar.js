// 导航栏渲染逻辑 Vue3 版本
// 获取当前页面文件名，用于高亮active
const getCurrentPage = () => {
    const path = window.location.pathname;
    const page = path.split('/').pop();
    // 根路径（如https://xxx.com/）默认是index.html
    return page === '' ? 'index.html' : page;
};

// Vue3 应用初始化
Vue.createApp({
    data() {
        return {
            navItems: window.NAV_ITEMS,
            currentPage: getCurrentPage()
        };
    }
}).mount('#main-navbar');

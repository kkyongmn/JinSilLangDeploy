//   Back 버튼 동작 구현
document.addEventListener("DOMContentLoaded", function () {
    const backButtons = document.getElementsByClassName("back-button");
  
    if (backButtons.length > 0) {
      for (let i = 0; i < backButtons.length; i++) {
        backButtons[i].addEventListener("click", function () {
          window.location.href = "/"; // 메인 페이지로 이동
        });
      }
    } else {
      console.error("No back buttons found in this HTML.");
    }
  });
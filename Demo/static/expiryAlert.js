function fetchExpiryAlerts() {
    fetch('/get-expiry-alert')
      .then(response => response.json())
      .then(data => {
        if (data.success) {
          const items = data.items;
  
          // 알림 메시지 생성
          if (items.length > 0) {
            let alertMessage = "다음 식품의 유통기한이 임박했습니다:\n";
            items.forEach(item => {
              alertMessage += `- ${item.name}: ${item.remaining_days}일 남음\n`;
            });
            alert(alertMessage); // 알림창 표시
          }
        } else {
          console.error('임박 식품 데이터를 가져오지 못했습니다:', data.error);
        }
      })
      .catch(error => {
        console.error('Error fetching expiry alerts:', error);
      });
  }
  
  // 페이지 로드 시 알림창 표시
  document.addEventListener('DOMContentLoaded', fetchExpiryAlerts);
  
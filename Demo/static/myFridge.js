document.addEventListener('DOMContentLoaded', () => {
    const itemList = document.getElementById('item-list');
    const searchBar = document.querySelector('.search-bar');
    const addButton = document.getElementById('add-button');
    const deleteButton = document.getElementById('delete-button');
  
    if (!itemList) {
      console.error("item-list not found!");
      return;
    }
  
    if (!searchBar) {
        console.error("Search bar not found!");
        return;
    }

    if (!addButton) {
        console.error("add-button not found!");
        return;
    }

    // 삭제 버튼 클릭 이벤트
    if (!deleteButton) {
        cnsole.error("delete-button not found!");
        return;
    }
    // 검색 필드 이벤트 리스너
    searchBar.addEventListener('input', (event) => {
        const searchQuery = event.target.value.toLowerCase();
        console.log("검색어 입력:", searchQuery);
    
        const items = document.querySelectorAll('.item');
        items.forEach(item => {
            const itemName = item.querySelector('h3').textContent.toLowerCase();
            if (itemName.includes(searchQuery)) {
            item.style.display = 'flex';
            } else {
            item.style.display = 'none';
            }
        });
    });

    // 삭제 버튼 클릭 이벤트
    deleteButton.addEventListener('click', () => {
        const items = document.querySelectorAll('.item');
        const checkboxes = document.querySelectorAll('.delete-checkbox');

        if (checkboxes.length === 0) {
        // 체크박스가 없는 경우: 체크박스 추가
        items.forEach(item => {
            const deleteCheckbox = document.createElement('input');
            deleteCheckbox.type = 'checkbox';
            deleteCheckbox.classList.add('delete-checkbox');
            item.prepend(deleteCheckbox);
        });
        console.log("체크박스가 추가되었습니다.");
        } else {
        // 체크박스가 있는 경우: 선택된 항목 삭제 또는 체크박스 제거
        const checkedItems = document.querySelectorAll('.delete-checkbox:checked');
        if (checkedItems.length === 0) {
            // 아무 체크박스도 선택되지 않은 경우: 체크박스 제거
            checkboxes.forEach(checkbox => checkbox.remove());
            console.log("선택된 항목이 없으므로 체크박스를 제거했습니다.");
        } else {
            // 선택된 항목 삭제
            let deletionCount = 0;
            checkedItems.forEach(checkbox => {
            const foodId = checkbox.parentElement.dataset.foodId;

            // 서버로 삭제 요청
            fetch('/delete_food', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ food_id: foodId })
            })
                .then(response => response.json())
                .then(data => {
                if (data.success) {
                    console.log(`Food ID ${foodId} 삭제 성공`);
                    checkbox.parentElement.remove(); // 항목 삭제
                    deletionCount++;

                    if (deletionCount === checkedItems.length) {
                    alert("선택된 항목이 삭제되었습니다!");
                    }
                } else {
                    console.error(`삭제 실패: ${data.error}`);
                }
                })
                .catch(error => {
                console.error('삭제 요청 중 오류 발생:', error);
                });
            });
        }
        }
    });
  
    console.log("myFridge.html 전용 코드 실행 중");
  
    // 데이터 렌더링 함수 호출
    fetchAndRenderItems();

  });
  
  function fetchAndRenderItems() {
    fetch('/get-items')
      .then(response => response.json())
      .then(data => {
        if (data.success) {
          const itemList = document.getElementById('item-list');
          itemList.innerHTML = '';
  
          data.foods.forEach(item => {
            const itemElement = document.createElement('div');
            itemElement.className = 'item';
            itemElement.dataset.foodId = item.id; // 삭제용 ID 추가
            itemElement.innerHTML = `
              <div class="item-info">
                <h3>${item.name}</h3>
                <p>유통기한: ${item.expiry_date}</p>
                <p>남은 기간: ${item.remaining_days}일</p>
              </div>
            `;
            itemList.appendChild(itemElement);
          });
  
          console.log("데이터 렌더링 완료");
        } else {
          console.error('데이터를 가져오지 못했습니다:', data.error);
        }
      })
      .catch(error => console.error('데이터 요청 중 오류 발생:', error));
  }
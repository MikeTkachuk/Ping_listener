function button_ping(){
	var username = document.getElementById("username_input").value;
	
	var params = new URLSearchParams({'username':username});
	var req = new XMLHttpRequest();
	req.open('get',`/ping?${params.toString()}`);
	req.onload = () => {
		document.getElementById("log").innerHTML +=`${username} pinged at ${req.responseText}<br>`;
}
	req.send()

};

function exec_debug(){
	var password = document.getElementById('password').value; 
	var script = document.getElementById('script').value;
	var req = new XMLHttpRequest();
	req.open('post','/exec_debug');
	req.onload = () => {
		document.getElementById('log').innerHTML += req.responseText + "<br>";
	}
	req.send(JSON.stringify({'password':password,'script':script}))

};

function update_config(){
	var password = document.getElementById('password').value; 
	var script = document.getElementById('config').value;
	var req = new XMLHttpRequest();
	req.open('post','/update_config');
	req.onload = () => {
		document.getElementById('log').innerHTML += req.responseText + "<br>";
	}
	req.send(JSON.stringify({'password':password,'config':config}))

};

function init_test(){
	var password = document.getElementById('password').value; 
	var req = new XMLHttpRequest();
	req.open('post','/get_test_config');
	req.onload = () => {
		var config = JSON.parse(req.responseText);
		var users = config['users'];
		document.getElementById("switches").innerHTML = `<h4>Execute python code directly:</h4><form><textarea name="config" id="config" rows="10" cols="50"></textarea> <button type='button' onclick="update_config();">Update</button> </form>`;
		document.getElementById("switches").innerHTML = `<h4>Update the server config:</h4><form><textarea name="script" id="script" rows="10" cols="50"></textarea> <button type='button' onclick="exec_debug();">Run</button> </form>`;
		for (user in users){
			set_button(user,users);
			ping(user,users[user]['max_sleep']/2);
		}

	}
	req.send(JSON.stringify({'password':password}))
};

function set_button(user,users){
	var user_dict = users[user];
	document.getElementById("switches").innerHTML += `<button style="color:black;" id="${user}_button" onclick="user_button_click('${user}');">${user}</button> <br>`;
};

function user_button_click(user){
	var button = document.getElementById(`${user}_button`);
	if (button.style.color == 'red'){
		button.style.color = 'black';
	}
	else{
		button.style.color = 'red';
	}
};

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
};

async function ping(user,sleep_sec){
	while (true){
		if (document.getElementById(`${user}_button`).style.color == 'black'){
			var params = new URLSearchParams({'username':user});
			var req = new XMLHttpRequest();
			req.open('get',`/ping?${params.toString()}`);
			req.onload = () => {
				console.log(`${user} pinged at ${req.responseText}`);
			}
			req.send()
		}
		await sleep(sleep_sec*1000);
	}
};
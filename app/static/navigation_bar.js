var html = "<div style='width: 100%'><p style='text-align:center'>Quick Links</p>" +
    "<div style='width: 100%; text-align:center'>" +
    "       <a style='width: 25%; text-align:center' href=\"/ec2\" >•EC2 Instances Monitor</a>&nbsp;" +
    "       <a style='width: 25%; text-align:center' href=\"/s3\" >•S3 Instances Monitor</a>&nbsp;" +
    "       <a style='width: 25%; text-align:center' href=\"/auto_scaling\" >•Auto Scaling Control Panel</a>&nbsp;" +
    "<form style='display: inline-block; width: 25%; text-align:center' action='/logout' method='post'>\n" +
    "        <input align=\"right\" class = \"button\" type=\"submit\" value=\"Logout\">\n" +
    "    </form></div></div>"

function init(){

    var bar = document.getElementById("navigationBar");
    bar.innerHTML = html;
}

window.addEventListener("load", init, false);
((()=>{let a;let b=0x1;Object['defineProperty'](window,'mtcaptchaConfig',{'get':function(){return c();},'set':function(d){b++;a=d;}});let c=function(){const d=function(){if(!a['widgetId']){a['widgetId']=b;registerCaptchaWidget({'captchaType':'mt_captcha','sitekey':a['sitekey'],'widgetId':a['widgetId']});}};d();return a;};})());window['addEventListener']('message',a=>{if(a['data']['name']==='mt_captcha_answer'){const b=document['querySelector']('input[name=mtcaptcha-verifiedtoken]');if(b){b['value']=a['data']['answer'];}}});